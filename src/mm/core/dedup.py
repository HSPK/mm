"""Duplicate detection — DB-based.

Looks up media entries in the database that share the same SHA-256 hash.
Also provides a helper for the importer to skip files already in the library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mm.db.sync_repo import SyncRepo


@dataclass
class DedupGroup:
    """A group of media entries sharing the same hash."""

    file_hash: str
    keep: Path
    duplicates: list[Path]


def find_duplicates(repo: SyncRepo) -> list[DedupGroup]:
    """Query the database for media with duplicate file hashes.

    For each group the largest file is marked as *keep*; the rest are
    duplicates.
    """
    groups_map = repo.find_duplicate_hashes()
    result: list[DedupGroup] = []
    for file_hash, media_list in groups_map.items():
        # Already sorted by file_size desc from DB query
        keep = Path(media_list[0].path)
        duplicates = [Path(m.path) for m in media_list[1:]]
        result.append(DedupGroup(file_hash=file_hash, keep=keep, duplicates=duplicates))
    return result


def is_duplicate(repo: SyncRepo, file_hash: str) -> bool:
    """Return True if a file with this hash already exists in the library."""
    return repo.hash_exists(file_hash) is not None
