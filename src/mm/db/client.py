"""Async database client with namespaced APIs."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import peewee_aio
from peewee import SQL

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
from mm.db.backend import DatabaseTarget
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

    def __init__(self, database_target: str | Path) -> None:
        self.target = DatabaseTarget.from_value(database_target)
        self.database = self.target.display
        self.db_path = self.target.local_path
        self.default_library_root = self.target.default_library_root
        self.manager = peewee_aio.Manager(self.target.manager_url)
        if self.target.local_path is not None:
            # Ensure Peewee's sync database has the real path. The async URL parser
            # and Peewee sync parser normalize absolute sqlite paths differently.
            self.manager.pw_database.init(str(self.target.local_path))
        database.initialize(self.manager.pw_database)
        for model in ALL_TABLES:
            self.manager.register(model)
        self.objects = self.manager
        self.source = DbSource(self.manager, self.default_library_root)

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
        await self.manager.create_tables(*ALL_TABLES, safe=True)
        if self.target.backend == "sqlite":
            with suppress(Exception):
                await self.manager.execute(
                    SQL("ALTER TABLE media ADD COLUMN deleted_at DATETIME DEFAULT NULL")
                )
