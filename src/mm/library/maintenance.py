"""Database maintenance workflows for media libraries."""

from __future__ import annotations

import datetime as dt
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mm.db.dto import FileSyncState, MediaSyncSnapshot
from mm.db.sync_client import DBClient
from mm.io import FileStorage
from mm.media.scanner import ScanResult, discover_media, save_media_metadata, scan_files
from mm.utils.parallel import map_items
from mm.utils.paths import make_relative_path, resolve_media_path

if TYPE_CHECKING:
    from mm.extractor.metadata import MetadataMode


@dataclass(frozen=True)
class MissingMediaPlan:
    total_records: int
    missing_ids: list[int]
    missing_paths: list[str]


@dataclass(frozen=True)
class OrphanCleanupResult:
    metadata: int
    media_tags: int
    tags: int


@dataclass(frozen=True)
class DiskFileState:
    path: str
    abs_path: str
    file_size: int
    mtime_ns: int


@dataclass(frozen=True)
class StaleSyncFile:
    media: MediaSyncSnapshot
    state_path: str
    abs_path: str


@dataclass(frozen=True)
class ChangedSyncFile:
    media: MediaSyncSnapshot
    disk: DiskFileState


@dataclass(frozen=True)
class LibrarySyncPlan:
    scan_id: str
    total_records: int
    disk_files: int
    stale: list[StaleSyncFile]
    changed: list[ChangedSyncFile]
    new: list[DiskFileState]
    unchanged_states: list[FileSyncState]

    @property
    def stale_ids(self) -> list[int]:
        return [item.media.id for item in self.stale]

    @property
    def stale_paths(self) -> list[str]:
        return [item.abs_path for item in self.stale]

    @property
    def changed_ids(self) -> list[int]:
        return [item.media.id for item in self.changed]

    @property
    def changed_paths(self) -> list[str]:
        return [item.disk.abs_path for item in self.changed]

    @property
    def new_paths(self) -> list[str]:
        return [item.abs_path for item in self.new]


@dataclass(frozen=True)
class RescanResult:
    scanned: int
    errors: int


@dataclass(frozen=True)
class LibrarySyncResult:
    deleted: int
    orphan_tags: int
    scanned: int
    indexed: int
    moved: int
    errors: int
    states_saved: int


def plan_missing_media_cleanup(
    db: DBClient,
    library_root: str | Path,
    *,
    storage: FileStorage,
) -> MissingMediaPlan:
    """Find DB rows whose files are missing from disk."""
    root = str(library_root)
    all_rows = db.media.paths()
    missing_ids: list[int] = []
    missing_paths: list[str] = []
    for media_id, stored_path in all_rows:
        abs_path = resolve_media_path(stored_path, root)
        if not storage.exists(abs_path):
            missing_ids.append(media_id)
            missing_paths.append(stored_path)
    return MissingMediaPlan(len(all_rows), missing_ids, missing_paths)


def delete_missing_media(db: DBClient, media_ids: list[int]) -> int:
    """Delete media rows by id."""
    if not media_ids:
        return 0
    return db.media.delete_rows(media_ids)


def cleanup_orphan_rows(db: DBClient) -> OrphanCleanupResult:
    """Delete rows that reference missing media records."""
    return OrphanCleanupResult(
        metadata=db.metadata.delete_orphans(),
        media_tags=db.tag.delete_orphan_links(),
        tags=db.tag.delete_orphans(),
    )


def plan_library_sync(
    db: DBClient,
    library_root: str | Path,
    *,
    storage: FileStorage,
    jobs: int = 0,
    on_progress: Callable[[int, int], None] | None = None,
) -> LibrarySyncPlan:
    """Find stale, changed, and new library files relative to persisted sync state."""
    root = str(library_root)
    scan_id = uuid.uuid4().hex
    media_rows = db.media.sync_snapshot()
    sync_state = db.sync_state.snapshot()
    disk_files = _discover_disk_file_states(root, storage=storage, jobs=jobs)
    disk_by_path = {item.path: item for item in disk_files}
    media_path_map = {_state_path_for_media(row.path, root): row for row in media_rows}

    stale: list[StaleSyncFile] = []
    changed: list[ChangedSyncFile] = []
    unchanged_states: list[FileSyncState] = []
    now = dt.datetime.now()

    for index, media in enumerate(media_rows, start=1):
        state_path = _state_path_for_media(media.path, root)
        disk = disk_by_path.get(state_path)
        if disk is None:
            stale.append(
                StaleSyncFile(
                    media=media,
                    state_path=state_path,
                    abs_path=resolve_media_path(media.path, root),
                )
            )
        elif _disk_changed(media, disk, sync_state.get(state_path)):
            changed.append(ChangedSyncFile(media=media, disk=disk))
        else:
            unchanged_states.append(
                _file_sync_state(disk, media.id, media.file_hash, scan_id, now)
            )
        if on_progress:
            on_progress(index, len(media_rows))

    new_files = [disk for disk in disk_files if disk.path not in media_path_map]

    return LibrarySyncPlan(
        scan_id=scan_id,
        total_records=len(media_rows),
        disk_files=len(disk_files),
        stale=stale,
        changed=changed,
        new=new_files,
        unchanged_states=unchanged_states,
    )


def delete_stale_media(db: DBClient, media_ids: list[int]) -> tuple[int, int]:
    """Delete stale media rows and orphan tags."""
    deleted = delete_missing_media(db, media_ids)
    orphan_tags = db.tag.delete_orphans() if deleted else 0
    return deleted, orphan_tags


def execute_library_sync(
    db: DBClient,
    plan: LibrarySyncPlan,
    *,
    jobs: int = 0,
    storage: FileStorage,
    metadata_mode: MetadataMode = "exiftool",
    on_scan_progress: Callable[[ScanResult], None] | None = None,
    on_metadata_progress: Callable[[int], None] | None = None,
    on_save_progress: Callable[[], None] | None = None,
    on_error: Callable[[ScanResult], None] | None = None,
) -> LibrarySyncResult:
    scan_targets = [item.disk for item in plan.changed] + plan.new
    disk_by_abs_path = {str(Path(item.abs_path).resolve()): item for item in scan_targets}
    now = dt.datetime.now()
    states: list[FileSyncState] = list(plan.unchanged_states)
    matched_stale_ids: set[int] = set()
    indexed = 0
    moved = 0
    errors = 0

    if scan_targets:
        results, errors = scan_files(
            [Path(item.abs_path) for item in scan_targets],
            jobs=jobs,
            storage=storage,
            backend="process",
            metadata_mode=metadata_mode,
            on_scan_progress=on_scan_progress,
            on_metadata_progress=on_metadata_progress,
            on_error=on_error,
        )
        stale_by_hash = _stale_files_by_hash(plan.stale)
        new_state_paths = {item.path for item in plan.new}

        for result in results:
            disk = disk_by_abs_path[str(Path(result.media.path).resolve())]
            if disk.path in new_state_paths and result.media.file_hash:
                match = _pop_stale_hash_match(stale_by_hash, result.media.file_hash)
                if match is not None:
                    db.media.update_path(
                        match.media.id,
                        disk.path,
                        Path(disk.path).name,
                        Path(disk.path).suffix.lower(),
                    )
                    matched_stale_ids.add(match.media.id)
                    moved += 1

            media_id = save_media_metadata(
                db,
                result.media,
                result.metadata,
                media_path=result.media.path,
            )
            states.append(_file_sync_state(disk, media_id, result.media.file_hash, plan.scan_id, now))
            indexed += 1
            if on_save_progress:
                on_save_progress()

    stale_to_delete = [item for item in plan.stale if item.media.id not in matched_stale_ids]
    deleted, orphan_tags = delete_stale_media(db, [item.media.id for item in stale_to_delete])
    db.sync_state.delete_paths([item.state_path for item in plan.stale])
    states_saved = db.sync_state.upsert_many(states)

    return LibrarySyncResult(
        deleted=deleted,
        orphan_tags=orphan_tags,
        scanned=indexed,
        indexed=indexed,
        moved=moved,
        errors=errors,
        states_saved=states_saved,
    )


def rescan_changed_media(
    db: DBClient,
    media_ids: list[int],
    paths: list[str],
    *,
    jobs: int = 0,
    storage: FileStorage,
    metadata_mode: MetadataMode = "exiftool",
    on_progress: Callable[[ScanResult], None] | None = None,
    on_error: Callable[[ScanResult], None] | None = None,
) -> RescanResult:
    """Re-scan changed files and store fresh metadata without deleting old rows first."""
    if not paths:
        return RescanResult(scanned=0, errors=0)

    results, errors = scan_files(
        [Path(path) for path in paths],
        jobs=jobs,
        storage=storage,
        backend="process",
        metadata_mode=metadata_mode,
        on_progress=on_progress,
        on_error=on_error,
    )
    for result in results:
        save_media_metadata(db, result.media, result.metadata, media_path=result.media.path)
    return RescanResult(scanned=len(results), errors=errors)


def _discover_disk_file_states(
    root: str,
    *,
    storage: FileStorage,
    jobs: int,
) -> list[DiskFileState]:
    paths = list(discover_media(Path(root), storage=storage))
    states = map_items(
        _build_disk_file_state,
        [(path, root, storage) for path in paths],
        jobs=jobs,
        backend="thread",
    )
    return sorted([state for state in states if state is not None], key=lambda state: state.path)


def _build_disk_file_state(args: tuple[Path, str, FileStorage]) -> DiskFileState | None:
    path, root, storage = args
    try:
        stat = storage.stat(path)
    except OSError:
        return None
    abs_path = str(storage.resolve(path))
    return DiskFileState(
        path=_state_path_for_abs_path(abs_path, root),
        abs_path=abs_path,
        file_size=stat.st_size,
        mtime_ns=getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)),
    )


def _state_path_for_media(stored_path: str, root: str) -> str:
    return _state_path_for_abs_path(resolve_media_path(stored_path, root), root)


def _state_path_for_abs_path(abs_path: str, root: str) -> str:
    return os.path.normpath(make_relative_path(str(Path(abs_path).resolve()), root))


def _disk_changed(
    media: MediaSyncSnapshot,
    disk: DiskFileState,
    state: FileSyncState | None,
) -> bool:
    if state is not None:
        return state.file_size != disk.file_size or state.mtime_ns != disk.mtime_ns
    if media.file_size != disk.file_size:
        return True
    if media.modified_at is None:
        return False
    media_mtime_ns = int(media.modified_at.timestamp() * 1_000_000_000)
    return abs(media_mtime_ns - disk.mtime_ns) > 1_000_000


def _file_sync_state(
    disk: DiskFileState,
    media_id: int,
    file_hash: str,
    scan_id: str,
    scanned_at: dt.datetime,
) -> FileSyncState:
    return FileSyncState(
        path=disk.path,
        media_id=media_id,
        file_size=disk.file_size,
        mtime_ns=disk.mtime_ns,
        file_hash=file_hash,
        last_seen_scan_id=scan_id,
        last_scanned_at=scanned_at,
    )


def _stale_files_by_hash(stale: list[StaleSyncFile]) -> dict[str, list[StaleSyncFile]]:
    by_hash: dict[str, list[StaleSyncFile]] = {}
    for item in stale:
        if item.media.file_hash:
            by_hash.setdefault(item.media.file_hash, []).append(item)
    return by_hash


def _pop_stale_hash_match(
    stale_by_hash: dict[str, list[StaleSyncFile]],
    file_hash: str,
) -> StaleSyncFile | None:
    matches = stale_by_hash.get(file_hash)
    if not matches:
        return None
    return matches.pop(0)
