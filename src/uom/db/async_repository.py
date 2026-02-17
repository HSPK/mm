"""Async Repository — composed from focused mixins."""

from __future__ import annotations

from pathlib import Path

import peewee_aio

from uom.db.mixins import (
    AlbumsMixin,
    CliMixin,
    ConfigMixin,
    MediaMixin,
    MetadataMixin,
    SmartAlbumsMixin,
    StatsMixin,
    TagsMixin,
    UsersMixin,
)
from uom.db.models import (
    ALL_TABLES,
    database,
)


class AsyncRepository(
    UsersMixin,
    MediaMixin,
    StatsMixin,
    TagsMixin,
    MetadataMixin,
    AlbumsMixin,
    SmartAlbumsMixin,
    CliMixin,
    ConfigMixin,
):
    """Async Peewee-aio repository — single entry point for all DB operations."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(Path(db_path).resolve())
        if database.database is None:
            database.init(self._db_path)
            database.allow_sync = True
        # The async backend (aiosqlite) strips one leading slash from the URL
        # path, so "aiosqlite:///" + "/abs/path" (4 slashes total) yields the
        # correct absolute path.  However peewee_aio's sync pw_database strips
        # TWO slashes, so we re-init it with the real path afterwards.
        self.manager = peewee_aio.Manager(f"aiosqlite:///{self._db_path}")
        self.manager.pw_database.init(self._db_path)
        for model in ALL_TABLES:
            self.manager.register(model)
        self.objects = self.manager

    # ── Lifecycle ─────────────────────────────────────────

    async def connect(self) -> None:
        async with self.manager:
            pass

    async def init_db(self) -> None:
        with self.manager.allow_sync():
            self.manager.pw_database.create_tables(ALL_TABLES)
            try:
                self.manager.pw_database.execute_sql(
                    "ALTER TABLE media ADD COLUMN deleted_at DATETIME DEFAULT NULL"
                )
            except Exception:
                pass
        if await self.count_users() == 0:
            await self.create_user(
                "admin", password="admin123", display_name="Admin", is_admin=True
            )
            print("[uom] Created default admin user: admin / admin123")
        await self._seed_smart_albums()
