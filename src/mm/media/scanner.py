"""Recursive media file scanner with hashing."""

from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mm.config import (
    ALL_MEDIA_EXTENSIONS,
    AUDIO_EXTENSIONS,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from mm.db.dto import Media, Metadata
from mm.db.models import MediaType
from mm.io import FileStorage
from mm.utils.hashing import file_hash
from mm.utils.parallel import MapBackend, map_items
from mm.utils.paths import make_relative_path

if TYPE_CHECKING:
    from mm.db.sync_client import DBClient


@dataclass
class ScanResult:
    """Result of scanning a single file — carries Media + Metadata DTOs directly."""

    media: Media
    metadata: Metadata
    error: str = ""


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------


def classify_extension(ext: str) -> MediaType | None:
    """Return the MediaType for a given (lower-case, dot-prefixed) extension."""
    if ext in PHOTO_EXTENSIONS:
        return MediaType.PHOTO
    if ext in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    if ext in AUDIO_EXTENSIONS:
        return MediaType.AUDIO
    return None


def discover_media(
    directory: Path,
    allowed_extensions: frozenset[str] | set[str] | None = None,
    *,
    storage: FileStorage,
) -> Generator[Path, None, None]:
    """Yield all supported media file paths under *directory*, skipping hidden files/dirs."""
    if allowed_extensions is None:
        allowed_extensions = ALL_MEDIA_EXTENSIONS

    yield from storage.iter_files(directory, allowed_extensions=allowed_extensions)


def scan_file(
    path: Path,
    compute_hash: bool = True,
    *,
    storage: FileStorage,
) -> Media:
    """Build a Media dataclass for one file on disk."""
    stat = storage.stat(path)
    ext = path.suffix.lower()
    mtype = classify_extension(ext) or MediaType.NOT_MEDIA
    return Media(
        path=str(path.resolve()),
        filename=path.name,
        extension=ext,
        media_type=mtype,
        file_size=stat.st_size,
        file_hash=file_hash(path, storage=storage) if compute_hash else "",
        created_at=datetime.fromtimestamp(stat.st_birthtime)
        if hasattr(stat, "st_birthtime")
        else datetime.fromtimestamp(stat.st_ctime),
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )


def scan_and_extract(
    path: Path,
    compute_hash: bool = True,
    *,
    storage: FileStorage,
) -> ScanResult:
    """Scan a file and extract its metadata, returning Media + Metadata directly."""
    try:
        from mm.extractor.metadata import extract_metadata

        media = scan_file(path, compute_hash=compute_hash, storage=storage)
        metadata = extract_metadata(path, 0)
        return ScanResult(media=media, metadata=metadata)
    except Exception as e:
        return ScanResult(
            media=Media(
                path=str(path.resolve()), filename=path.name, extension=path.suffix.lower()
            ),
            metadata=Metadata(),
            error=str(e),
        )


def save_media_metadata(
    db: DBClient,
    media: Media,
    metadata: Metadata,
    media_path: str | Path,
) -> int:
    """Save media and metadata DTOs to the database at an explicit media path."""
    from dataclasses import replace

    config = db.library_config.get()
    library_root = config.library_root

    path = Path(media_path)
    if not path.is_absolute():
        path = library_root / path
    resolved_path = str(path.resolve())
    media_to_save = replace(
        media,
        path=make_relative_path(resolved_path, library_root),
        filename=path.name,
        extension=path.suffix.lower(),
    )

    media_id = db.media.upsert(media_to_save)

    metadata_to_save = replace(metadata, media_id=media_id)
    db.metadata.upsert(metadata_to_save)
    return media_id


def scan_file_worker(args: tuple[str, bool, FileStorage]) -> ScanResult:
    """Worker function for mapped scanning that unpacks arguments."""
    path_str, compute_hash, storage = args
    return scan_and_extract(Path(path_str), compute_hash=compute_hash, storage=storage)


def scan_files(
    files: list[Path],
    *,
    compute_hash: bool = True,
    storage: FileStorage,
    jobs: int = 0,
    backend: MapBackend = "process",
    on_progress: Callable[[ScanResult], None] | None = None,
    on_error: Callable[[ScanResult], None] | None = None,
) -> tuple[list[ScanResult], int]:
    """Scan files with configurable map backend and return results plus error count."""
    work_items = [(str(path.resolve()), compute_hash, storage) for path in files]
    if not work_items:
        return [], 0

    errors = 0
    results: list[ScanResult] = []

    def _handle_result(result: ScanResult) -> None:
        nonlocal errors
        if result.error:
            errors += 1
            if on_error:
                on_error(result)
        else:
            results.append(result)
        if on_progress:
            on_progress(result)

    map_items(
        scan_file_worker,
        work_items,
        jobs=jobs if jobs > 0 else min(mp.cpu_count(), 8),
        backend=backend,
        on_result=_handle_result,
    )
    return results, errors
