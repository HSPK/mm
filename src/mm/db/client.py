"""Async database client with namespaced APIs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import peewee_aio

from mm.db.api import (
    AlbumsApi,
    DbSource,
    LibraryConfigApi,
    MediaApi,
    MetadataApi,
    SmartAlbumsApi,
    StatsApi,
    TagsApi,
    UsersApi,
)
from mm.db.models import (
    ALL_TABLES,
    database,
)

if TYPE_CHECKING:
    from mm.db.sync_client import DBClient

AnyDBClient: TypeAlias = "AsyncDBClient | DBClient"


class AsyncDBClient:
    """Async Peewee-aio database client with namespaced APIs."""

    user: UsersApi
    media: MediaApi
    stats: StatsApi
    tag: TagsApi
    metadata: MetadataApi
    album: AlbumsApi
    smart_album: SmartAlbumsApi
    library_config: LibraryConfigApi

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).resolve()
        self._db_path = str(self.db_path)
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
        self.source = DbSource(self.manager, self.db_path)

        self.user = UsersApi(self.source)
        self.media = MediaApi(self.source)
        self.stats = StatsApi(self.source)
        self.tag = TagsApi(self.source)
        self.metadata = MetadataApi(self.source)
        self.album = AlbumsApi(self.source)
        self.smart_album = SmartAlbumsApi(self.source)
        self.library_config = LibraryConfigApi(self.source)

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
