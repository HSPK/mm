"""Library config database API."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from mm.db.api._source import DbApi
from mm.db.models import LibraryConfigModel
from mm.library.settings import LibraryConfig


class LibraryConfigApi(DbApi):
    objects: peewee_aio.Manager

    async def get(self) -> LibraryConfig:
        """Return the validated library config."""
        rows = await self.objects.fetchall(LibraryConfigModel.select())
        values = {row.key: row.value for row in rows}
        values.setdefault("library_root", str(self.source.db_path.parent))
        return LibraryConfig.model_validate(values)

    async def set(self, config: LibraryConfig) -> None:
        """Persist the validated library config."""
        now = dt.datetime.now()
        for key, value in config.model_dump(mode="json").items():
            try:
                await self.objects.get(LibraryConfigModel, key=key)
                await self.objects.execute(
                    LibraryConfigModel.update(value=value, updated_at=now).where(
                        LibraryConfigModel.key == key
                    )
                )
            except LibraryConfigModel.DoesNotExist:
                await self.objects.create(
                    LibraryConfigModel,
                    key=key,
                    value=value,
                    updated_at=now,
                )
