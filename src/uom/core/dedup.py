"""Duplicate detection strategies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

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
    """Find files with same stem differing only in .jpg/.jpeg extension.

    Keeps the larger file.
    """
    jpg_files: dict[tuple[Path, str], Path] = {}
    jpeg_files: dict[tuple[Path, str], Path] = {}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        for name in files:
            if name.startswith("."):
                continue
            p = root_path / name
            ext = p.suffix.lower()
            stem = p.stem.lower()
            key = (root_path, stem)
            if ext == ".jpg":
                jpg_files[key] = p
            elif ext == ".jpeg":
                jpeg_files[key] = p

    pairs: list[DedupPair] = []
    common_keys = set(jpeg_files.keys()) & set(jpg_files.keys())
    for key in common_keys:
        jpeg_path = jpeg_files[key]
        jpg_path = jpg_files[key]
        if jpeg_path.stat().st_size >= jpg_path.stat().st_size:
            pairs.append(DedupPair(keep=jpeg_path, remove=jpg_path, reason="same-name"))
        else:
            pairs.append(DedupPair(keep=jpg_path, remove=jpeg_path, reason="same-name"))
    return pairs


# ---------------------------------------------------------------------------
# Strategy: identical file hash
# ---------------------------------------------------------------------------


def find_hash_duplicates(directory: Path, progress: bool = True) -> list[DedupPair]:
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
    items = click.progressbar(to_hash, label="Hashing files") if progress else to_hash
    iter_items = items.__enter__() if hasattr(items, "__enter__") else items  # type: ignore[union-attr]
    try:
        for p in iter_items:
            try:
                h = file_hash(p)
            except OSError:
                continue
            hash_map.setdefault(h, []).append(p)
    finally:
        if hasattr(items, "__exit__"):
            items.__exit__(None, None, None)  # type: ignore[union-attr]

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
) -> list[DedupPair]:
    if strategy == DedupStrategy.NAME:
        return find_name_duplicates(directory)
    if strategy == DedupStrategy.HASH:
        return find_hash_duplicates(directory, progress=progress)
    raise ValueError(f"Unknown strategy: {strategy}")
