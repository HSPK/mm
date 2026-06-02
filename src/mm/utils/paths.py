"""Path helpers shared across the application."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_media_path(stored_path: str, library_root: str | Path) -> str:
    """Resolve a stored media path relative to a library root."""
    if os.path.isabs(stored_path):
        return stored_path
    return os.path.normpath(os.path.join(str(library_root), stored_path))


def make_relative_path(abs_path: str, library_root: str | Path) -> str:
    """Convert an absolute path to one relative to *library_root*."""
    return os.path.relpath(abs_path, str(library_root))
