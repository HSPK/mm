from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mm.config import get_config
from mm.db.sync_client import DBClient
from mm.io import FileStorage
from mm.media.thumbnails import cache_dir_for_library, get_thumbnail
from mm.utils.parallel import map_items
from mm.utils.paths import resolve_media_path


@dataclass(frozen=True)
class ThumbnailCacheStats:
    cache_dir: Path
    file_count: int
    total_size: int


@dataclass(frozen=True)
class ThumbnailBuildResult:
    total: int
    generated: int
    cached: int
    failed: int


@dataclass(frozen=True)
class _ThumbnailTask:
    media_id: int
    source_path: str
    size: str
    cache_dir: Path
    force: bool
    storage: FileStorage


@dataclass(frozen=True)
class _ThumbnailTaskResult:
    generated: bool
    cached: bool
    failed: bool


def thumbnail_cache_dir(library_id: str | None, cache_base: Path | None = None) -> Path:
    return cache_dir_for_library(library_id, base=cache_base)


def thumbnail_cache_stats(
    library_id: str | None,
    *,
    cache_base: Path | None = None,
    storage: FileStorage,
) -> ThumbnailCacheStats:
    cache_dir = thumbnail_cache_dir(library_id, cache_base)
    file_count = 0
    total_size = 0
    for path in storage.rglob_files(cache_dir):
        file_count += 1
        total_size += storage.get_size(path)
    return ThumbnailCacheStats(cache_dir=cache_dir, file_count=file_count, total_size=total_size)


def build_thumbnail_cache(
    db: DBClient,
    library_root: str | Path,
    library_id: str | None,
    *,
    sizes: list[str] | None = None,
    cache_base: Path | None = None,
    force: bool = False,
    jobs: int = 0,
    storage: FileStorage,
    on_progress: Callable[[_ThumbnailTaskResult], None] | None = None,
) -> ThumbnailBuildResult:
    valid_sizes = get_config().thumbnails.sizes
    selected_sizes = sizes or list(valid_sizes)
    unknown = sorted(set(selected_sizes) - set(valid_sizes))
    if unknown:
        raise ValueError(f"Unknown thumbnail size(s): {', '.join(unknown)}")

    cache_dir = thumbnail_cache_dir(library_id, cache_base)
    tasks: list[_ThumbnailTask] = []
    for media in db.media.list():
        if media.id is None or media.deleted_at is not None:
            continue
        source_path = resolve_media_path(media.path, library_root)
        if not storage.exists(source_path):
            continue
        for size in selected_sizes:
            tasks.append(
                _ThumbnailTask(
                    media_id=media.id,
                    source_path=source_path,
                    size=size,
                    cache_dir=cache_dir,
                    force=force,
                    storage=storage,
                )
            )

    results = map_items(
        _build_one_thumbnail,
        tasks,
        jobs=jobs,
        backend="thread",
        on_result=on_progress,
    )
    return ThumbnailBuildResult(
        total=len(tasks),
        generated=sum(1 for result in results if result.generated),
        cached=sum(1 for result in results if result.cached),
        failed=sum(1 for result in results if result.failed),
    )


def _build_one_thumbnail(task: _ThumbnailTask) -> _ThumbnailTaskResult:
    dest = task.cache_dir / task.size / f"{task.media_id}.webp"
    cached = _is_fresh(dest, task.source_path, task.storage)
    if task.force and task.storage.exists(dest):
        task.storage.delete_file(dest, missing_ok=True)
        cached = False
    thumb = get_thumbnail(
        task.source_path,
        task.media_id,
        task.size,
        task.cache_dir,
        storage=task.storage,
    )
    if thumb is None:
        return _ThumbnailTaskResult(generated=False, cached=False, failed=True)
    return _ThumbnailTaskResult(generated=not cached, cached=cached, failed=False)


def _is_fresh(dest: Path, source_path: str, storage: FileStorage) -> bool:
    if not storage.exists(dest):
        return False
    try:
        return storage.get_mtime(source_path) <= storage.get_mtime(dest)
    except OSError:
        return False
