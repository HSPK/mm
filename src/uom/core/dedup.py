"""Duplicate detection strategies."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from uom.config import ALL_MEDIA_EXTENSIONS
from uom.core.scanner import file_hash


class DedupStrategy(str, Enum):
    NAME = "name"  # same stem, different extension (.jpg vs .jpeg)
    HASH = "hash"  # identical SHA-256 across any path
    # VISUAL = "visual" # embedding-based — future


@dataclass
class DedupPair:
    """A (keep, remove) pair of duplicate files."""

    keep: Path
    remove: Path
    reason: str = ""


# ---------------------------------------------------------------------------
# Strategy: same name, different jpg/jpeg extension
# ---------------------------------------------------------------------------


def find_name_duplicates(directory: Path) -> list[DedupPair]:
    """Find media files with the same stem across any subdirectory.

    When multiple files share the same stem (case-insensitive), the largest
    file is kept and the rest are marked for removal.
    """
    stem_map: dict[str, list[Path]] = {}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        for name in files:
            if name.startswith("."):
                continue
            p = root_path / name
            if p.suffix.lower() not in ALL_MEDIA_EXTENSIONS:
                continue
            stem = p.stem.lower()
            stem_map.setdefault(stem, []).append(p)

    pairs: list[DedupPair] = []
    for stem, paths in stem_map.items():
        if len(paths) < 2:
            continue
        # Keep the largest file; remove the rest
        paths.sort(key=lambda p: p.stat().st_size, reverse=True)
        keep = paths[0]
        for dup in paths[1:]:
            pairs.append(DedupPair(keep=keep, remove=dup, reason="same-name"))
    return pairs


# ---------------------------------------------------------------------------
# Strategy: identical file hash
# ---------------------------------------------------------------------------


def find_hash_duplicates(
    directory: Path,
    progress: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[DedupPair]:
    """Find files with identical SHA-256.  Keeps the largest copy."""
    # Phase 1: group by size (files with unique size can't be duplicates)
    size_map: dict[int, list[Path]] = {}
    all_files: list[Path] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        for name in files:
            if name.startswith("."):
                continue
            p = root_path / name
            if p.suffix.lower() in ALL_MEDIA_EXTENSIONS:
                all_files.append(p)

    for p in all_files:
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        size_map.setdefault(sz, []).append(p)

    # Only hash files with duplicate sizes
    candidates = [paths for paths in size_map.values() if len(paths) > 1]
    to_hash: list[Path] = [p for group in candidates for p in group]

    hash_map: dict[str, list[Path]] = {}
    for i, p in enumerate(to_hash):
        try:
            h = file_hash(p)
        except OSError:
            continue
        hash_map.setdefault(h, []).append(p)
        if on_progress:
            on_progress(i + 1, len(to_hash))

    pairs: list[DedupPair] = []
    for h, paths in hash_map.items():
        if len(paths) < 2:
            continue
        # Keep the largest (or first if same size), remove the rest
        paths.sort(key=lambda p: p.stat().st_size, reverse=True)
        keep = paths[0]
        for dup in paths[1:]:
            pairs.append(DedupPair(keep=keep, remove=dup, reason="hash-dup"))
    return pairs


# ---------------------------------------------------------------------------
# Unified dispatcher
# ---------------------------------------------------------------------------


def find_duplicates(
    directory: Path,
    strategy: DedupStrategy = DedupStrategy.NAME,
    progress: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[DedupPair]:
    if strategy == DedupStrategy.NAME:
        return find_name_duplicates(directory)
    if strategy == DedupStrategy.HASH:
        return find_hash_duplicates(directory, progress=progress, on_progress=on_progress)
    raise ValueError(f"Unknown strategy: {strategy}")
