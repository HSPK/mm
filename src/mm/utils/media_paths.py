"""Utilities for validating and repairing stored media paths."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from mm.config import get_config
from mm.db.dto import Media, Metadata
from mm.db.sync_client import DBClient
from mm.io import FileStorage
from mm.media.importer import build_dest_path
from mm.media.scanner import discover_media
from mm.utils.hashing import file_hash
from mm.utils.paths import make_relative_path, resolve_media_path


@dataclass(frozen=True)
class MediaPathUpdate:
    media_id: int
    old_path: str
    new_path: str
    filename: str
    extension: str
    method: str
    destination: Path


@dataclass(frozen=True)
class MediaPathIssue:
    media_id: int
    path: str
    reason: str


@dataclass(frozen=True)
class MediaPathConflict:
    media_id: int
    path: str
    owner_id: int


@dataclass(frozen=True)
class MediaPathDeletion:
    media_id: int
    path: str
    resolved_path: Path
    reason: str


@dataclass(frozen=True)
class MediaPathRepairPlan:
    library_root: Path
    scanned: int
    bad_paths: int
    updates: list[MediaPathUpdate]
    deletions: list[MediaPathDeletion]
    unresolved: list[MediaPathIssue]
    conflicts: list[MediaPathConflict]
    by_method: dict[str, int]


def plan_media_path_repairs(
    db: DBClient,
    library_root: Path,
    template: str | None = None,
    *,
    storage: FileStorage,
) -> MediaPathRepairPlan:
    """Plan safe media path repairs without writing to the database."""
    if template is None:
        template = get_config().import_.template
    root = library_root.resolve()
    media_rows = [media for media in db.media.list() if media.id is not None]
    metadata_by_id = db.metadata.get_for_ids([media.id for media in media_rows if media.id])
    existing_paths = {media.path: media.id for media in media_rows if media.id is not None}

    candidates = [
        (media, stored_path, _is_inside(stored_path, root), storage.exists(stored_path))
        for media in media_rows
        for stored_path in [Path(resolve_media_path(media.path, root))]
        if not _is_inside(stored_path, root) or not storage.exists(stored_path)
    ]
    bad_paths = sum(1 for _media, _path, is_inside, _exists in candidates if not is_inside)
    if not candidates:
        return MediaPathRepairPlan(
            library_root=root,
            scanned=len(media_rows),
            bad_paths=0,
            updates=[],
            deletions=[],
            unresolved=[],
            conflicts=[],
            by_method={},
        )

    size_index = _build_size_index(root, storage=storage)
    hash_cache: dict[Path, str] = {}
    updates: list[MediaPathUpdate] = []
    deletions: list[MediaPathDeletion] = []
    unresolved: list[MediaPathIssue] = []
    conflicts: list[MediaPathConflict] = []
    by_method: Counter[str] = Counter()

    for media, stored_path, is_inside, path_exists in candidates:
        media_id = _media_id(media)
        if is_inside:
            deletions.append(MediaPathDeletion(media_id, media.path, stored_path, "missing-file"))
            continue

        metadata = metadata_by_id.get(media_id)
        destination, method = find_media_destination(
            media,
            metadata,
            root,
            template,
            size_index,
            hash_cache,
            storage=storage,
        )
        if destination is None:
            if not path_exists:
                deletions.append(
                    MediaPathDeletion(media_id, media.path, stored_path, "missing-file")
                )
                continue
            unresolved.append(MediaPathIssue(media_id, media.path, method))
            continue

        rel_path = make_relative_path(str(destination), root)
        owner = existing_paths.get(rel_path)
        if owner is not None and owner != media_id:
            conflicts.append(MediaPathConflict(media_id, rel_path, owner))
            continue

        updates.append(
            MediaPathUpdate(
                media_id=media_id,
                old_path=media.path,
                new_path=rel_path,
                filename=destination.name,
                extension=destination.suffix.lower(),
                method=method,
                destination=destination,
            )
        )
        by_method[method] += 1

    return MediaPathRepairPlan(
        library_root=root,
        scanned=len(media_rows),
        bad_paths=bad_paths,
        updates=updates,
        deletions=deletions,
        unresolved=unresolved,
        conflicts=conflicts,
        by_method=dict(by_method),
    )


def apply_media_path_repairs(db: DBClient, updates: list[MediaPathUpdate]) -> int:
    """Apply planned media path repairs to the database."""
    updated = 0
    for item in updates:
        updated += db.media.update_path(item.media_id, item.new_path, item.filename, item.extension)
    return updated


def delete_missing_media_rows(db: DBClient, deletions: list[MediaPathDeletion]) -> int:
    """Delete database rows whose files cannot be found."""
    if not deletions:
        return 0
    return db.media.delete_rows([item.media_id for item in deletions])


def find_media_destination(
    media: Media,
    metadata: Metadata | None,
    library_root: Path,
    template: str,
    size_index: dict[int, list[Path]],
    hash_cache: dict[Path, str],
    *,
    storage: FileStorage,
) -> tuple[Path | None, str]:
    """Find the copied destination for a media row whose stored path is wrong."""
    expected = build_dest_path(
        media,
        metadata,
        template,
        library_root,
        default_date=media.modified_at,
    )
    if _path_matches(media, expected, hash_cache, storage=storage):
        return expected, "template"

    stem = expected.stem
    suffix = expected.suffix
    parent = expected.parent
    for i in range(1, 1000):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not storage.exists(candidate):
            break
        if _path_matches(media, candidate, hash_cache, storage=storage):
            return candidate, "template-conflict"

    expected_name = media.filename or expected.name
    for candidate in size_index.get(media.file_size, []):
        if candidate.name == expected_name and _path_matches(
            media,
            candidate,
            hash_cache,
            storage=storage,
        ):
            return candidate, "filename"

    if media.file_hash:
        for candidate in size_index.get(media.file_size, []):
            if _path_matches(media, candidate, hash_cache, storage=storage):
                return candidate, "hash"

    return None, "missing"


def _build_size_index(
    library_root: Path,
    *,
    storage: FileStorage,
) -> dict[int, list[Path]]:
    index: defaultdict[int, list[Path]] = defaultdict(list)
    for path in discover_media(library_root, storage=storage):
        try:
            index[storage.get_size(path)].append(path)
        except OSError:
            continue
    return dict(index)


def _path_matches(
    media: Media,
    path: Path,
    hash_cache: dict[Path, str],
    *,
    storage: FileStorage,
) -> bool:
    try:
        stat = storage.stat(path)
    except OSError:
        return False
    if not storage.is_file(path) or stat.st_size != media.file_size:
        return False
    if not media.file_hash:
        return True

    actual_hash = hash_cache.get(path)
    if actual_hash is None:
        try:
            actual_hash = file_hash(path, storage=storage)
        except OSError:
            return False
        hash_cache[path] = actual_hash
    return actual_hash == media.file_hash


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True


def _media_id(media: Media) -> int:
    if media.id is None:
        raise ValueError("media row is missing an id")
    return media.id
