"""Database schema migrations."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from typing import Any, Protocol

from peewee import (
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
    SmartAlbumModel,
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
)
