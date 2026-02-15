"""Recursive media file scanner with hashing."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

from uom.config import (
    ALL_MEDIA_EXTENSIONS,
    AUDIO_EXTENSIONS,
    HASH_CHUNK_SIZE,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from uom.db.models import MediaType
from uom.db.repository import Media


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


def discover_media(directory: Path) -> Generator[Path, None, None]:
    """Yield all supported media file paths under *directory*, skipping hidden files/dirs."""
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories in-place so os.walk won't descend
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            p = Path(root) / name
            if p.suffix.lower() in ALL_MEDIA_EXTENSIONS:
                yield p


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
