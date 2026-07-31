"""Tests for the database database client."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mm.db.dto import Media, Metadata
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
    media_id = db.media.upsert(m)
    db.metadata.upsert(Metadata(media_id=media_id, date_taken=datetime(2026, 6, 17)))
    placeholder_id = db.media.upsert(
        Media(
            path="/tmp/placeholder.jpg",
            filename="placeholder.jpg",
            extension=".jpg",
            media_type=MediaType.PHOTO,
            file_size=512,
            file_hash="placeholder",
        )
    )
    db.metadata.upsert(Metadata(media_id=placeholder_id, date_taken=datetime(1980, 1, 1)))
    assert db.media.count() == 2
    assert db.stats.total_size() == 2560

    dist = db.stats.type_distribution()
    assert dist["video"] == 1
    assert db.stats.timeline() == [{"period": "2026-06-17", "count": 1}]


def test_db_client_migrates_legacy_schema(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE media (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                extension VARCHAR(16) NOT NULL,
                media_type VARCHAR(16) NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                file_hash VARCHAR(64) NOT NULL DEFAULT '',
                rating INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME,
                modified_at DATETIME,
                scanned_at DATETIME NOT NULL
            );
            CREATE TABLE smart_albums (
                id INTEGER PRIMARY KEY,
                key VARCHAR(256) NOT NULL UNIQUE,
                section VARCHAR(64),
                title VARCHAR(256) NOT NULL,
                subtitle VARCHAR(512),
                icon VARCHAR(64),
                color VARCHAR(64),
                filters TEXT,
                generator VARCHAR(64),
                generator_config TEXT,
                position INTEGER,
                is_system INTEGER,
                enabled INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            );
            INSERT INTO smart_albums (
                key, section, title, subtitle, icon, color, filters, generator_config,
                position, is_system, enabled
            ) VALUES (
                'legacy', 'library', 'Legacy', NULL, 'images', NULL, '{}', '{}', 0, 1, 1
            );
            """
        )

    client = DBClient(db_path)
    client.close()

    with sqlite3.connect(db_path) as conn:
        media_columns = {row[1] for row in conn.execute("PRAGMA table_info(media)")}
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        color = conn.execute("SELECT color FROM smart_albums WHERE key = 'legacy'").fetchone()[0]
        migrations = {
            row[0] for row in conn.execute("SELECT name FROM schema_migrations ORDER BY name")
        }
        organizer_columns = {row[1] for row in conn.execute("PRAGMA table_info(organizer_media)")}

    assert "deleted_at" in media_columns
    assert "file_sync_state" in tables
    assert color == ""
    assert migrations == {
        "0001_add_media_deleted_at",
        "0002_normalize_smart_album_schema",
        "0003_create_file_sync_state",
        "0004_create_organizer_media",
        "0005_create_organizer_rename_log",
        "0006_create_organizer_jobs",
        "0007_migrate_organizer_jobs_to_jobs",
        "0008_create_job_events",
        "0009_add_organizer_media_light_columns",
        "0010_create_video_state",
        "0011_create_video_probe_cache",
        "0012_create_scrape_cache",
        "0013_add_organizer_audio_columns",
        "0014_add_organizer_music_ids",
        "0015_add_organizer_identity_and_scope",
        "0016_add_job_idempotency",
        "0017_add_job_active_claim",
        "0018_backfill_organizer_source_roots",
        "0019_add_organizer_sync_fingerprints",
        "0020_add_localized_music_identity",
        "0021_complete_album_artist_identity",
    }
    assert {
        "audio_duration",
        "audio_mime_type",
        "music_album_id",
        "music_artist_id",
        "item_uid",
        "revision",
        "source_root",
        "file_size",
        "mtime_ns",
        "sidecar_signature",
        "scan_version",
        "music_track_id",
        "album_artist",
        "music_album_artist_id",
        "music_title_variants",
        "music_artist_variants",
        "music_album_artist_variants",
        "music_album_variants",
    } <= organizer_columns


def test_db_client_adds_unique_columns_after_migrating_legacy_rows(tmp_path: Path):
    db_path = tmp_path / "legacy-unique-columns.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE organizer_media (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                source_kind VARCHAR(16) NOT NULL,
                media_type VARCHAR(16) NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                missing INTEGER NOT NULL DEFAULT 0,
                first_seen_at DATETIME NOT NULL,
                last_seen_at DATETIME NOT NULL
            );
            INSERT INTO organizer_media (
                path, source_kind, media_type, first_seen_at, last_seen_at
            ) VALUES
                ('/tmp/one.mkv', 'movies', 'movie', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                ('/tmp/two.mkv', 'movies', 'movie', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                ('/tmp/track.flac', 'music', 'track', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            UPDATE organizer_media
            SET payload = '{
                "path": "/tmp/track.flac",
                "media_type": "track",
                "title": "Silence",
                "artist": "Jay Chou",
                "album": "Fantasy",
                "metadata_ids": {
                    "musicbrainz_recording": "recording-mbid",
                    "musicbrainz_release_group": "release-group-mbid",
                    "musicbrainz_artist": "artist-mbid"
                }
            }'
            WHERE path = '/tmp/track.flac';

            CREATE TABLE jobs (
                id VARCHAR(64) PRIMARY KEY,
                kind VARCHAR(32) NOT NULL,
                status VARCHAR(16) NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                title VARCHAR(256) NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL DEFAULT '{}',
                result TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
            INSERT INTO jobs (id, kind, status, created_at, updated_at) VALUES
                ('job-one', 'sync', 'done', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                ('job-two', 'sync', 'done', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """
        )

    client = DBClient(db_path)
    client.close()

    with sqlite3.connect(db_path) as conn:
        organizer_ids = conn.execute("SELECT item_uid FROM organizer_media ORDER BY id").fetchall()
        organizer_indexes = {row[1] for row in conn.execute("PRAGMA index_list(organizer_media)")}
        job_claims = conn.execute("SELECT active_claim FROM jobs ORDER BY id").fetchall()
        job_indexes = {row[1] for row in conn.execute("PRAGMA index_list(jobs)")}
        track_ids = conn.execute(
            "SELECT music_track_id, music_album_id, music_artist_id, "
            "music_album_artist_id "
            "FROM organizer_media WHERE media_type = 'track'"
        ).fetchone()

    assert all(item_uid for (item_uid,) in organizer_ids)
    assert len({item_uid for (item_uid,) in organizer_ids}) == 3
    assert "organizer_media_item_uid" in organizer_indexes
    from mm.server.music_catalog import (
        album_artist_id_for_item,
        album_id_for_item,
        artist_id_for_item,
        track_id_for_item,
    )
    from mm.server.organizer_schemas import OrganizerItem

    expected_item = OrganizerItem(
        path="/tmp/track.flac",
        media_type="track",
        title="Silence",
        artist="Jay Chou",
        album="Fantasy",
        metadata_ids={
            "musicbrainz_recording": "recording-mbid",
            "musicbrainz_release_group": "release-group-mbid",
            "musicbrainz_artist": "artist-mbid",
        },
    )
    assert track_ids == (
        track_id_for_item(expected_item),
        album_id_for_item(expected_item),
        artist_id_for_item(expected_item),
        album_artist_id_for_item(expected_item),
    )
    assert job_claims == [(None,), (None,)]
    assert "jobs_active_claim" in job_indexes


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
