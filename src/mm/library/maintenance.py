"""Database maintenance workflows for media libraries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mm.db.sync_client import DBClient
from mm.io import FileStorage, local_storage
from mm.media.scanner import ScanResult, save_media_metadata, scan_files
from mm.utils.paths import resolve_media_path


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
class LibrarySyncPlan:
    total_records: int
    stale_ids: list[int]
    stale_paths: list[str]
    changed_ids: list[int]
    changed_paths: list[str]


@dataclass(frozen=True)
class RescanResult:
    scanned: int
    errors: int


def plan_missing_media_cleanup(
    db: DBClient,
    library_root: str | Path,
    *,
    storage: FileStorage = local_storage,
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
    storage: FileStorage = local_storage,
) -> LibrarySyncPlan:
    """Find stale and changed DB rows relative to files on disk."""
    root = str(library_root)
    all_rows = db.media.paths()
    stale_ids: list[int] = []
    stale_paths: list[str] = []
    changed_ids: list[int] = []
    changed_paths: list[str] = []

    for media_id, stored_path in all_rows:
        abs_path = resolve_media_path(stored_path, root)
        if not storage.exists(abs_path):
            stale_ids.append(media_id)
            stale_paths.append(abs_path)
            continue

        media = db.media.get(media_id)
        if media and media.file_size != storage.get_size(abs_path):
            changed_ids.append(media_id)
            changed_paths.append(abs_path)

    return LibrarySyncPlan(
        total_records=len(all_rows),
        stale_ids=stale_ids,
        stale_paths=stale_paths,
        changed_ids=changed_ids,
        changed_paths=changed_paths,
    )


def delete_stale_media(db: DBClient, media_ids: list[int]) -> tuple[int, int]:
    """Delete stale media rows and orphan tags."""
    deleted = delete_missing_media(db, media_ids)
    orphan_tags = db.tag.delete_orphans() if deleted else 0
    return deleted, orphan_tags


def rescan_changed_media(
    db: DBClient,
    media_ids: list[int],
    paths: list[str],
    *,
    jobs: int = 0,
    storage: FileStorage = local_storage,
    on_progress: Callable[[ScanResult], None] | None = None,
    on_error: Callable[[ScanResult], None] | None = None,
) -> RescanResult:
    """Delete changed rows, re-scan their files, and store fresh metadata."""
    if not paths:
        return RescanResult(scanned=0, errors=0)

    db.media.delete_rows(media_ids)
    results, errors = scan_files(
        [Path(path) for path in paths],
        jobs=jobs,
        storage=storage,
        backend="process",
        on_progress=on_progress,
        on_error=on_error,
    )
    for result in results:
        save_media_metadata(db, result.media, result.metadata, media_path=result.media.path)
    return RescanResult(scanned=len(results), errors=errors)
