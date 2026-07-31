"""Database schema migrations."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from peewee import (
    BigIntegerField,
    CharField,
    Database,
    DateTimeField,
    FloatField,
    IntegerField,
    SmallIntegerField,
    TextField,
)
from playhouse.migrate import PostgresqlMigrator, SqliteMigrator, migrate

from mm.db.backend import DatabaseBackend
from mm.db.models import (
    FileSyncStateModel,
    JobEventModel,
    JobModel,
    OrganizerMediaModel,
    OrganizerRenameLogModel,
    SchemaMigrationModel,
    ScrapeCacheModel,
    SmartAlbumModel,
    VideoProbeCacheModel,
    VideoStateModel,
)


class Migrator(Protocol):
    def add_column(self, table: str, column: str, field: Any) -> Any: ...


Migration = Callable[[Database, Migrator], None]


def run_migrations(db: Database, backend: DatabaseBackend) -> None:
    """Run pending migrations against the bound Peewee database."""
    close_after = db.is_closed()
    if close_after:
        db.connect()
    try:
        db.create_tables([SchemaMigrationModel], safe=True)
        applied = {row.name for row in SchemaMigrationModel.select(SchemaMigrationModel.name)}
        migrator = _migrator_for(db, backend)

        for name, migration in _MIGRATIONS:
            if name in applied:
                continue
            with db.atomic():
                migration(db, migrator)
                SchemaMigrationModel.create(name=name, applied_at=dt.datetime.now())
    finally:
        if close_after:
            db.close()


def _migrator_for(db: Database, backend: DatabaseBackend) -> Migrator:
    if backend == "sqlite":
        return SqliteMigrator(db)
    return PostgresqlMigrator(db)


def _has_table(db: Database, table: str) -> bool:
    return table in db.get_tables()


def _has_column(db: Database, table: str, column: str) -> bool:
    if not _has_table(db, table):
        return False
    return any(metadata.name == column for metadata in db.get_columns(table))


def _add_column_if_missing(
    db: Database,
    migrator: Migrator,
    table: str,
    column: str,
    field: Any,
) -> None:
    if not _has_column(db, table, column):
        migrate(migrator.add_column(table, column, field))


def _add_media_deleted_at(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db,
        migrator,
        "media",
        "deleted_at",
        DateTimeField(null=True, default=None),
    )


def _normalize_smart_album_schema(db: Database, migrator: Migrator) -> None:
    for column, field in (
        ("section", CharField(max_length=64, default="custom")),
        ("subtitle", CharField(max_length=512, default="")),
        ("icon", CharField(max_length=64, default="images")),
        ("color", CharField(max_length=64, default="")),
        ("filters", TextField(default="{}")),
        ("generator", CharField(max_length=64, null=True, default=None)),
        ("generator_config", TextField(default="{}")),
        ("position", IntegerField(default=0)),
        ("is_system", SmallIntegerField(default=1)),
        ("enabled", SmallIntegerField(default=1)),
        ("created_at", DateTimeField(default=dt.datetime.now)),
        ("updated_at", DateTimeField(default=dt.datetime.now)),
    ):
        _add_column_if_missing(db, migrator, "smart_albums", column, field)

    now = dt.datetime.now()
    for field, value in (
        (SmartAlbumModel.section, "custom"),
        (SmartAlbumModel.subtitle, ""),
        (SmartAlbumModel.icon, "images"),
        (SmartAlbumModel.color, ""),
        (SmartAlbumModel.filters, "{}"),
        (SmartAlbumModel.generator_config, "{}"),
        (SmartAlbumModel.position, 0),
        (SmartAlbumModel.is_system, 1),
        (SmartAlbumModel.enabled, 1),
        (SmartAlbumModel.created_at, now),
        (SmartAlbumModel.updated_at, now),
    ):
        if _has_column(db, "smart_albums", field.column_name):
            SmartAlbumModel.update({field: value}).where(field.is_null()).execute()


def _create_file_sync_state(db: Database, migrator: Migrator) -> None:
    db.create_tables([FileSyncStateModel], safe=True)


def _create_organizer_media(db: Database, migrator: Migrator) -> None:
    db.create_tables([OrganizerMediaModel], safe=True)


def _create_organizer_rename_log(db: Database, migrator: Migrator) -> None:
    db.create_tables([OrganizerRenameLogModel], safe=True)


def _create_organizer_jobs(db: Database, migrator: Migrator) -> None:
    db.create_tables([JobModel], safe=True)


def _migrate_organizer_jobs_to_jobs(db: Database, migrator: Migrator) -> None:
    db.create_tables([JobModel], safe=True)
    if not _has_table(db, "organizer_jobs"):
        return
    columns = (
        "id",
        "kind",
        "status",
        "progress",
        "title",
        "message",
        "detail",
        "payload",
        "result",
        "error",
        "created_at",
        "updated_at",
    )
    names = ", ".join(columns)
    db.execute_sql(
        f"""
        INSERT INTO jobs ({names})
        SELECT {names}
        FROM organizer_jobs
        WHERE NOT EXISTS (
            SELECT 1 FROM jobs WHERE jobs.id = organizer_jobs.id
        )
        """
    )
    db.execute_sql("DROP TABLE IF EXISTS organizer_jobs")


def _create_job_events(db: Database, migrator: Migrator) -> None:
    db.create_tables([JobEventModel], safe=True)


def _add_organizer_media_light_columns(db: Database, migrator: Migrator) -> None:
    db.create_tables([OrganizerMediaModel], safe=True)
    _add_column_if_missing(db, migrator, "organizer_media", "title", TextField(default=""))
    _add_column_if_missing(db, migrator, "organizer_media", "artist", TextField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "album", TextField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "year", IntegerField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "season", IntegerField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "episode", IntegerField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "disc", IntegerField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "track", IntegerField(null=True))
    _add_column_if_missing(db, migrator, "organizer_media", "parse_template", TextField(null=True))
    _add_column_if_missing(
        db, migrator, "organizer_media", "parse_relative_path", TextField(null=True)
    )
    _add_column_if_missing(db, migrator, "organizer_media", "confidence", FloatField(default=0.0))
    _add_column_if_missing(db, migrator, "organizer_media", "is_new", SmallIntegerField(default=0))
    _add_column_if_missing(
        db, migrator, "organizer_media", "has_metadata", SmallIntegerField(default=0)
    )
    _add_column_if_missing(
        db, migrator, "organizer_media", "has_images", SmallIntegerField(default=0)
    )
    _add_column_if_missing(
        db, migrator, "organizer_media", "has_subtitles", SmallIntegerField(default=0)
    )
    _add_column_if_missing(
        db, migrator, "organizer_media", "has_lyrics", SmallIntegerField(default=0)
    )


def _create_video_state(db: Database, migrator: Migrator) -> None:
    db.create_tables([VideoStateModel], safe=True)


def _create_video_probe_cache(db: Database, migrator: Migrator) -> None:
    db.create_tables([VideoProbeCacheModel], safe=True)


def _create_scrape_cache(db: Database, migrator: Migrator) -> None:
    db.create_tables([ScrapeCacheModel], safe=True)


def _add_organizer_audio_columns(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db, migrator, "organizer_media", "audio_duration", FloatField(null=True, default=None)
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "audio_mime_type",
        CharField(max_length=128, null=True, default=None),
    )
    db.execute_sql(
        "CREATE INDEX IF NOT EXISTS organizer_media_music_catalog "
        "ON organizer_media (source_kind, media_type, missing)"
    )


def _add_organizer_music_ids(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "music_album_id",
        CharField(max_length=64, null=True, default=None),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "music_artist_id",
        CharField(max_length=64, null=True, default=None),
    )
    from mm.server.music_catalog import album_id_for_path, artist_id_for_name

    rows = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.path,
        OrganizerMediaModel.artist,
    ).where(
        (OrganizerMediaModel.source_kind == "music") & (OrganizerMediaModel.media_type == "track")
    )
    for row in rows:
        OrganizerMediaModel.update(
            music_album_id=album_id_for_path(Path(row.path)),
            music_artist_id=artist_id_for_name(row.artist),
        ).where(OrganizerMediaModel.id == row.id).execute()


def _add_organizer_identity_and_scope(db: Database, migrator: Migrator) -> None:
    import uuid

    from mm.server.organizer_sources import configured_root_for_path

    _add_column_if_missing(
        db, migrator, "organizer_media", "item_uid", CharField(max_length=64, null=True)
    )
    _add_column_if_missing(db, migrator, "organizer_media", "revision", IntegerField(default=1))
    _add_column_if_missing(db, migrator, "organizer_media", "source_root", TextField(null=True))
    identity_rows = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.item_uid,
    ).where(OrganizerMediaModel.item_uid.is_null())
    for row in identity_rows:
        OrganizerMediaModel.update(item_uid=uuid.uuid4().hex, revision=1).where(
            OrganizerMediaModel.id == row.id
        ).execute()
    source_rows = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.path,
        OrganizerMediaModel.source_root,
    ).where(OrganizerMediaModel.source_root.is_null())
    for row in source_rows:
        root = configured_root_for_path(Path(row.path))
        if root is not None:
            OrganizerMediaModel.update(source_root=str(root)).where(
                OrganizerMediaModel.id == row.id
            ).execute()
    db.execute_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS organizer_media_item_uid ON organizer_media (item_uid)"
    )
    db.execute_sql(
        "CREATE INDEX IF NOT EXISTS organizer_media_source_root "
        "ON organizer_media (source_root, missing)"
    )


def _add_job_idempotency(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db, migrator, "jobs", "idempotency_key", CharField(max_length=256, null=True)
    )
    _add_column_if_missing(
        db, migrator, "jobs", "payload_hash", CharField(max_length=64, null=True)
    )
    db.execute_sql(
        "CREATE INDEX IF NOT EXISTS jobs_idempotency "
        "ON jobs (kind, idempotency_key, payload_hash, status)"
    )


def _add_job_active_claim(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db,
        migrator,
        "jobs",
        "active_claim",
        CharField(max_length=320, null=True, default=None),
    )
    db.execute_sql("CREATE UNIQUE INDEX IF NOT EXISTS jobs_active_claim ON jobs (active_claim)")


def _backfill_organizer_source_roots(db: Database, migrator: Migrator) -> None:
    from mm.server.organizer_sources import configured_root_for_path

    rows = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.path,
        OrganizerMediaModel.source_root,
    ).where(OrganizerMediaModel.source_root.is_null())
    for row in rows:
        root = configured_root_for_path(Path(row.path))
        if root is not None:
            OrganizerMediaModel.update(source_root=str(root)).where(
                OrganizerMediaModel.id == row.id
            ).execute()


def _add_organizer_sync_fingerprints(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "file_size",
        BigIntegerField(default=0),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "mtime_ns",
        BigIntegerField(default=0),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "sidecar_signature",
        CharField(max_length=64, default=""),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "scan_version",
        SmallIntegerField(default=0),
    )


def _add_localized_music_identity(db: Database, migrator: Migrator) -> None:
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "album_artist",
        TextField(null=True, default=None),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "music_track_id",
        CharField(max_length=64, null=True, default=None),
    )
    _add_column_if_missing(
        db,
        migrator,
        "organizer_media",
        "music_album_artist_id",
        CharField(max_length=64, null=True, default=None),
    )
    for column in (
        "music_title_variants",
        "music_artist_variants",
        "music_album_artist_variants",
        "music_album_variants",
    ):
        _add_column_if_missing(
            db,
            migrator,
            "organizer_media",
            column,
            TextField(default="{}"),
        )
    from mm.server.music_catalog import (
        album_artist_id_for_item,
        album_id_for_item,
        artist_id_for_item,
        track_id_for_item,
    )
    from mm.server.organizer_schemas import OrganizerItem

    rows = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.path,
        OrganizerMediaModel.item_uid,
        OrganizerMediaModel.title,
        OrganizerMediaModel.artist,
        OrganizerMediaModel.album_artist,
        OrganizerMediaModel.album,
        OrganizerMediaModel.payload,
        OrganizerMediaModel.music_track_id,
        OrganizerMediaModel.music_album_id,
        OrganizerMediaModel.music_artist_id,
        OrganizerMediaModel.music_album_artist_id,
    ).where(
        (OrganizerMediaModel.source_kind == "music") & (OrganizerMediaModel.media_type == "track")
    )
    for row in rows:
        try:
            item = OrganizerItem.model_validate_json(row.payload)
        except (ValueError, TypeError):
            item = OrganizerItem(
                path=row.path,
                media_type="track",
                title=row.title,
            )
        title = row.title or item.title
        artist = row.artist or item.artist
        album = row.album or item.album
        album_artist = row.album_artist or item.album_artist or artist
        item = item.model_copy(
            update={
                "path": row.path,
                "item_uid": row.item_uid,
                "media_type": "track",
                "title": title,
                "artist": artist,
                "album_artist": album_artist,
                "album": album,
            }
        )
        title_variants = item.metadata_title_variants or {"und": title}
        artist_variants = item.metadata_artist_variants or ({"und": artist} if artist else {})
        album_artist_variants = item.metadata_album_artist_variants or (
            {"und": album_artist} if album_artist else {}
        )
        album_variants = item.metadata_album_variants or ({"und": album} if album else {})
        OrganizerMediaModel.update(
            music_track_id=track_id_for_item(
                item,
                existing_id=row.music_track_id,
                item_uid=row.item_uid,
            ),
            title=title,
            artist=artist,
            album=album,
            music_album_id=album_id_for_item(
                item,
                existing_id=row.music_album_id,
            ),
            music_artist_id=artist_id_for_item(
                item,
                existing_id=row.music_artist_id,
            ),
            music_album_artist_id=album_artist_id_for_item(
                item,
                existing_id=row.music_album_artist_id,
            ),
            album_artist=album_artist,
            music_title_variants=json.dumps(title_variants, ensure_ascii=False),
            music_artist_variants=json.dumps(artist_variants, ensure_ascii=False),
            music_album_artist_variants=json.dumps(
                album_artist_variants,
                ensure_ascii=False,
            ),
            music_album_variants=json.dumps(album_variants, ensure_ascii=False),
        ).where(OrganizerMediaModel.id == row.id).execute()


_MIGRATIONS: tuple[tuple[str, Migration], ...] = (
    ("0001_add_media_deleted_at", _add_media_deleted_at),
    ("0002_normalize_smart_album_schema", _normalize_smart_album_schema),
    ("0003_create_file_sync_state", _create_file_sync_state),
    ("0004_create_organizer_media", _create_organizer_media),
    ("0005_create_organizer_rename_log", _create_organizer_rename_log),
    ("0006_create_organizer_jobs", _create_organizer_jobs),
    ("0007_migrate_organizer_jobs_to_jobs", _migrate_organizer_jobs_to_jobs),
    ("0008_create_job_events", _create_job_events),
    ("0009_add_organizer_media_light_columns", _add_organizer_media_light_columns),
    ("0010_create_video_state", _create_video_state),
    ("0011_create_video_probe_cache", _create_video_probe_cache),
    ("0012_create_scrape_cache", _create_scrape_cache),
    ("0013_add_organizer_audio_columns", _add_organizer_audio_columns),
    ("0014_add_organizer_music_ids", _add_organizer_music_ids),
    ("0015_add_organizer_identity_and_scope", _add_organizer_identity_and_scope),
    ("0016_add_job_idempotency", _add_job_idempotency),
    ("0017_add_job_active_claim", _add_job_active_claim),
    ("0018_backfill_organizer_source_roots", _backfill_organizer_source_roots),
    ("0019_add_organizer_sync_fingerprints", _add_organizer_sync_fingerprints),
    ("0020_add_localized_music_identity", _add_localized_music_identity),
    ("0021_complete_album_artist_identity", _add_localized_music_identity),
)
