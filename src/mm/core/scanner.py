"""Recursive media file scanner with hashing."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mm.config import (
    ALL_MEDIA_EXTENSIONS,
    AUDIO_EXTENSIONS,
    HASH_CHUNK_SIZE,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from mm.db.dto import Media, Metadata
from mm.db.models import MediaType

if TYPE_CHECKING:
    from mm.db.sync_repo import SyncRepo


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


def quick_hash(path: Path, num_chunks: int = 4, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Return a fast SHA-256 hash of the first *num_chunks* chunks of a file.

    Useful for cheap duplicate pre-screening before computing the full hash.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for _ in range(num_chunks):
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_hash(path: Path, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def discover_media(
    directory: Path, allowed_extensions: frozenset[str] | set[str] | None = None
) -> Generator[Path, None, None]:
    """Yield all supported media file paths under *directory*, skipping hidden files/dirs."""
    if allowed_extensions is None:
        allowed_extensions = ALL_MEDIA_EXTENSIONS

    for root, dirs, files in os.walk(directory):
        # Skip hidden directories in-place so os.walk won't descend
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in allowed_extensions:
                yield Path(root) / name


def scan_file(path: Path, compute_hash: bool = True) -> Media:
    """Build a Media dataclass for one file on disk."""
    stat = path.stat()
    ext = path.suffix.lower()
    mtype = classify_extension(ext) or MediaType.NOT_MEDIA
    return Media(
        path=str(path.resolve()),
        filename=path.name,
        extension=ext,
        media_type=mtype,
        file_size=stat.st_size,
        file_hash=file_hash(path) if compute_hash else "",
        created_at=datetime.fromtimestamp(stat.st_birthtime)
        if hasattr(stat, "st_birthtime")
        else datetime.fromtimestamp(stat.st_ctime),
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )


def scan_and_extract(path: Path, compute_hash: bool = True) -> ScanResult:
    """Scan a file and extract its metadata, returning Media + Metadata directly."""
    try:
        from mm.core.metadata import extract_metadata

        media = scan_file(path, compute_hash=compute_hash)
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


def save_scan_result(repo: SyncRepo, result: ScanResult) -> int:
    """Save a ScanResult to the database.

    Reads *library_root* from the repo config so stored paths are relative,
    making the library directory fully portable.
    """
    from dataclasses import replace

    library_root = repo.get_config("library_root")

    media = result.media
    if library_root:
        media = replace(media, path=os.path.relpath(media.path, library_root))

    media_id = repo.upsert_media(media)

    metadata = replace(result.metadata, media_id=media_id)
    repo.upsert_metadata(metadata)
    return media_id


def process_pool_worker(args: tuple[str, bool]) -> ScanResult:
    """Worker function for ProcessPoolExecutor that unpacks arguments."""
    path_str, compute_hash = args
    return scan_and_extract(Path(path_str), compute_hash=compute_hash)
