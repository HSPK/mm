"""Recursive media file scanner with hashing."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from mm.config import (
    ALL_MEDIA_EXTENSIONS,
    AUDIO_EXTENSIONS,
    HASH_CHUNK_SIZE,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from mm.db.dto import Media, Metadata
from mm.db.models import MediaType


@dataclass
class ScanResult:
    """Serialisable result combining file stats and extracted metadata."""

    path: str
    filename: str
    extension: str
    media_type: str
    file_size: int
    file_hash: str
    created_at: str  # ISO format or ""
    modified_at: str
    # metadata fields
    md_date_taken: str
    md_camera_make: str
    md_camera_model: str
    md_lens_model: str
    md_focal_length: float | None
    md_aperture: float | None
    md_shutter_speed: str
    md_iso: int | None
    md_width: int | None
    md_height: int | None
    md_duration: float | None
    md_gps_lat: float | None
    md_gps_lon: float | None
    md_orientation: int | None
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
    mtype = classify_extension(ext) or MediaType.PHOTO
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
    """Scan a file and extract its metadata, handling errors gracefully."""
    try:
        from mm.core.metadata import extract_metadata  # lazy import

        media = scan_file(path, compute_hash=compute_hash)

        # Extract metadata (use dummy ID 0)
        md = extract_metadata(path, 0)

        return ScanResult(
            path=media.path,
            filename=media.filename,
            extension=media.extension,
            media_type=media.media_type.value,
            file_size=media.file_size,
            file_hash=media.file_hash,
            created_at=media.created_at.isoformat() if media.created_at else "",
            modified_at=media.modified_at.isoformat() if media.modified_at else "",
            md_date_taken=md.date_taken.isoformat() if md.date_taken else "",
            md_camera_make=md.camera_make,
            md_camera_model=md.camera_model,
            md_lens_model=md.lens_model,
            md_focal_length=md.focal_length,
            md_aperture=md.aperture,
            md_shutter_speed=md.shutter_speed,
            md_iso=md.iso,
            md_width=md.width,
            md_height=md.height,
            md_duration=md.duration,
            md_gps_lat=md.gps_lat,
            md_gps_lon=md.gps_lon,
            md_orientation=md.orientation,
        )
    except Exception as e:
        # Fallback for error case
        return ScanResult(
            path=str(path.resolve()),
            filename=path.name,
            extension=path.suffix.lower(),
            media_type=MediaType.PHOTO.value,
            file_size=0,
            file_hash="",
            created_at="",
            modified_at="",
            md_date_taken="",
            md_camera_make="",
            md_camera_model="",
            md_lens_model="",
            md_focal_length=None,
            md_aperture=None,
            md_shutter_speed="",
            md_iso=None,
            md_width=None,
            md_height=None,
            md_duration=None,
            md_gps_lat=None,
            md_gps_lon=None,
            md_orientation=None,
            error=str(e),
        )


def save_scan_result(
    repo: Any, result: ScanResult, library_root: Path | str | None = None
) -> int:
    """Save a ScanResult to the database using the provided repository.

    If *library_root* is given, the stored path will be relative to it so the
    library directory is fully portable.
    """

    stored_path = result.path
    if library_root is not None:
        stored_path = os.path.relpath(result.path, str(library_root))

    media = Media(
        path=stored_path,
        filename=result.filename,
        extension=result.extension,
        media_type=MediaType(result.media_type),
        file_size=result.file_size,
        file_hash=result.file_hash,
        created_at=datetime.fromisoformat(result.created_at)
        if result.created_at
        else None,
        modified_at=datetime.fromisoformat(result.modified_at)
        if result.modified_at
        else None,
    )
    media_id = repo.upsert_media(media)

    md = Metadata(
        media_id=media_id,
        date_taken=datetime.fromisoformat(result.md_date_taken)
        if result.md_date_taken
        else None,
        camera_make=result.md_camera_make,
        camera_model=result.md_camera_model,
        lens_model=result.md_lens_model,
        focal_length=result.md_focal_length,
        aperture=result.md_aperture,
        shutter_speed=result.md_shutter_speed,
        iso=result.md_iso,
        width=result.md_width,
        height=result.md_height,
        duration=result.md_duration,
        gps_lat=result.md_gps_lat,
        gps_lon=result.md_gps_lon,
        orientation=result.md_orientation,
    )
    repo.upsert_metadata(md)
    return media_id


def process_pool_worker(args: tuple[str, bool]) -> ScanResult:
    """Worker function for ProcessPoolExecutor that unpacks arguments."""
    path_str, compute_hash = args
    return scan_and_extract(Path(path_str), compute_hash=compute_hash)
