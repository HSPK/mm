"""Hash helpers for file-like storage backends."""

from __future__ import annotations

import hashlib
from pathlib import Path

from mm.config import get_config
from mm.io import FileStorage


def quick_hash(
    path: Path,
    num_chunks: int = 4,
    chunk_size: int | None = None,
    *,
    storage: FileStorage,
) -> str:
    """Return a fast SHA-256 hash of the first *num_chunks* chunks of a file."""
    if chunk_size is None:
        chunk_size = get_config().hashing.chunk_size
    h = hashlib.sha256()
    with storage.open(path, "rb") as f:
        for _ in range(num_chunks):
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_hash(
    path: Path,
    chunk_size: int | None = None,
    *,
    storage: FileStorage,
) -> str:
    """Return the SHA-256 hex digest of a file."""
    if chunk_size is None:
        chunk_size = get_config().hashing.chunk_size
    h = hashlib.sha256()
    with storage.open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()
