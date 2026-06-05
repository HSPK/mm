"""Tests for the database database client."""

from __future__ import annotations

from pathlib import Path

from mm.db.dto import Media
from mm.db.models import MediaType, TagSource
from mm.db.sync_client import DBClient
from mm.library.settings import LibraryConfig


def test_upsert_and_get_media(db: DBClient):
    m = Media(
        path="/tmp/test.jpg",
        filename="test.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=1024,
        file_hash="abc123",
    )
    mid = db.media.upsert(m)
    assert mid > 0

    got = db.media.by_path("/tmp/test.jpg")
    assert got is not None
    assert got.file_hash == "abc123"


def test_namespaced_api_works(db: DBClient):
    media = Media(
        path="/tmp/ns.jpg",
        filename="ns.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=256,
        file_hash="ns123",
    )

    media_id = db.media.upsert(media)

    assert db.media.get(media_id) is not None
    assert db.media.by_path("/tmp/ns.jpg") is not None
    db.library_config.set(LibraryConfig(library_root="/tmp"))
    assert db.library_config.get().library_root == Path("/tmp").resolve()


def test_short_namespaced_api_names(db: DBClient):
    assert db.user.count() == 0
    user = db.user.create("admin", "secret")
    assert user.username == "admin"
    assert db.user.verify("admin", "secret") is not None

    album = db.album.create("Trip")
    assert album["name"] == "Trip"
    assert db.album.list()[0]["id"] == album["id"]
    assert db.album.rename(album["id"], "Trip 2")
    assert db.album.delete(album["id"])


def test_tag_operations(db: DBClient):
    # Create media first
    m = Media(
        path="/tmp/tag_test.jpg",
        filename="tag_test.jpg",
        extension=".jpg",
        media_type=MediaType.PHOTO,
        file_size=512,
        file_hash="def456",
    )
    mid = db.media.upsert(m)

    tag = db.tag.get_or_create("beach", source=TagSource.MANUAL)
    assert tag.id is not None
    assert tag.name == "beach"

    # Re-get should return same
    tag2 = db.tag.get_or_create("Beach")  # test normalisation
    assert tag2.id == tag.id

    db.tag.add_media(mid, tag.id)
    tags = db.tag.for_media(mid)
    assert len(tags) == 1
    assert tags[0][0].name == "beach"

    # Search by tag
    ids = db.tag.media_ids(["beach"])
    assert mid in ids

    # Remove
    db.tag.remove_media(mid, tag.id)
    tags = db.tag.for_media(mid)
    assert len(tags) == 0


def test_count_and_stats(db: DBClient):
    assert db.media.count() == 0
    m = Media(
        path="/tmp/stats.mp4",
        filename="stats.mp4",
        extension=".mp4",
        media_type=MediaType.VIDEO,
        file_size=2048,
        file_hash="ghi789",
    )
    db.media.upsert(m)
    assert db.media.count() == 1
    assert db.stats.total_size() == 2048

    dist = db.stats.type_distribution()
    assert dist["video"] == 1


def test_library_id_generated_on_first_read(db: DBClient):
    """library_id is a non-empty UUID4 string generated on the first get()."""
    import uuid

    config = db.library_config.get()
    assert config.library_id, "library_id must be non-empty"
    # Must be a valid UUID4
    parsed = uuid.UUID(config.library_id, version=4)
    assert str(parsed) == config.library_id


def test_library_id_is_stable_across_reads(db: DBClient):
    """Repeated get() calls return the same library_id."""
    id1 = db.library_config.get().library_id
    id2 = db.library_config.get().library_id
    assert id1 == id2


def test_library_id_is_unique_across_libraries(tmp_path: Path):
    """Two separate library databases have different library_ids."""
    db_a = DBClient(tmp_path / "a.db")
    db_b = DBClient(tmp_path / "b.db")
    try:
        id_a = db_a.library_config.get().library_id
        id_b = db_b.library_config.get().library_id
        assert id_a != id_b
    finally:
        db_a.close()
        db_b.close()


def test_library_id_preserved_after_config_update(db: DBClient):
    """Setting other config values does not change the library_id."""
    original_id = db.library_config.get().library_id

    current = db.library_config.get()
    db.library_config.set(LibraryConfig(library_name="Updated", library_root=current.library_root))

    assert db.library_config.get().library_id == original_id


def test_library_id_race_returns_existing_value(db: DBClient):
    """Concurrent first-readers must agree on the same library_id (no IntegrityError)."""

    # Call _ensure_library_id twice. The second call hits the
    # IntegrityError path (PK collision on key='library_id') and must
    # swallow it and return the value the first call inserted.
    async def both():
        a = await db._client.library_config._ensure_library_id()
        b = await db._client.library_config._ensure_library_id()
        return a, b

    first, second = db._run(both())
    assert first == second
    assert db.library_config.get().library_id == first
