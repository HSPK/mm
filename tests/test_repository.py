"""Tests for the database repository."""

from __future__ import annotations

from mm.db.dto import Media
from mm.db.models import MediaType, TagSource
from mm.db.sync_repo import SyncRepo


def test_upsert_and_get_media(repo: SyncRepo):
    m = Media(
        path="/tmp/test.jpg",
        filename="test.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=1024,
        file_hash="abc123",
    )
    mid = repo.upsert_media(m)
    assert mid > 0

    got = repo.get_media_by_path("/tmp/test.jpg")
    assert got is not None
    assert got.file_hash == "abc123"


def test_tag_operations(repo: SyncRepo):
    # Create media first
    m = Media(
        path="/tmp/tag_test.jpg",
        filename="tag_test.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=512,
        file_hash="def456",
    )
    mid = repo.upsert_media(m)

    tag = repo.get_or_create_tag("beach", source=TagSource.MANUAL)
    assert tag.id is not None
    assert tag.name == "beach"

    # Re-get should return same
    tag2 = repo.get_or_create_tag("Beach")  # test normalisation
    assert tag2.id == tag.id

    repo.add_media_tag(mid, tag.id)
    tags = repo.tags_for_media(mid)
    assert len(tags) == 1
    assert tags[0][0].name == "beach"

    # Search by tag
    ids = repo.media_ids_by_tags(["beach"])
    assert mid in ids

    # Remove
    repo.remove_media_tag(mid, tag.id)
    tags = repo.tags_for_media(mid)
    assert len(tags) == 0


def test_count_and_stats(repo: SyncRepo):
    assert repo.count_media() == 0
    m = Media(
        path="/tmp/stats.mp4",
        filename="stats.mp4",
        extension=".mp4",
        media_type=MediaType.VIDEO,
        file_size=2048,
        file_hash="ghi789",
    )
    repo.upsert_media(m)
    assert repo.count_media() == 1
    assert repo.total_size() == 2048

    dist = repo.type_distribution()
    assert dist["video"] == 1
