"""Tests for the dedup module."""

from __future__ import annotations

from pathlib import Path

from mm.core.dedup import find_duplicates, is_duplicate
from mm.db.sync_repo import SyncRepo


def _make_repo(tmp_path: Path) -> SyncRepo:
    """Create a temporary SyncRepo with a fresh DB."""
    db_path = tmp_path / "test.db"
    return SyncRepo(db_path)


def test_find_duplicates(tmp_path: Path):
    """Media with the same hash in the DB should be grouped."""
    repo = _make_repo(tmp_path)
    from mm.db.dto import Media
    from mm.db.models import MediaType

    # Insert two media entries with the same hash
    m1 = Media(
        path="a.jpg",
        filename="a.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=200,
        file_hash="aaa111",
    )
    m2 = Media(
        path="b.jpg",
        filename="b.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=100,
        file_hash="aaa111",
    )
    # And one unique entry
    m3 = Media(
        path="c.jpg",
        filename="c.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=300,
        file_hash="bbb222",
    )
    repo.upsert_media(m1)
    repo.upsert_media(m2)
    repo.upsert_media(m3)

    groups = find_duplicates(repo)
    assert len(groups) == 1
    # Largest file (200 bytes) is kept
    assert groups[0].keep == Path("a.jpg")
    assert groups[0].duplicates == [Path("b.jpg")]


def test_is_duplicate(tmp_path: Path):
    repo = _make_repo(tmp_path)
    from mm.db.dto import Media
    from mm.db.models import MediaType

    m = Media(
        path="x.jpg",
        filename="x.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=100,
        file_hash="abc123",
    )
    repo.upsert_media(m)

    assert is_duplicate(repo, "abc123") is True
    assert is_duplicate(repo, "nonexistent") is False
    assert is_duplicate(repo, "") is False
