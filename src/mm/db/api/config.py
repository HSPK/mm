"""Library config database API."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from mm.db.api._source import DbApi
from mm.db.models import LibraryConfigModel
from mm.library.settings import LibraryConfig


class LibraryConfigApi(DbApi):
    objects: peewee_aio.Manager

    async def get(self) -> LibraryConfig:
        """Return the validated library config.

        On first access (or for libraries created before ``library_id`` was
        introduced) a stable UUID4 is generated and immediately persisted so
        that subsequent reads return the same value.
        """
        rows = await self.objects.fetchall(LibraryConfigModel.select())
        values = {row.key: row.value for row in rows}
        values.setdefault("library_root", str(self.source.default_library_root))

        # Auto-generate a stable library_id if not yet stored.
        if not values.get("library_id"):
            new_id = str(uuid.uuid4())
            now = dt.datetime.now()
            await self.objects.create(
                LibraryConfigModel,
                key="library_id",
                value=new_id,
                updated_at=now,
            )
            values["library_id"] = new_id

        return LibraryConfig.model_validate(values)

    async def set(self, config: LibraryConfig) -> None:
        """Persist the validated library config.

        ``library_id`` is managed exclusively by :meth:`get` (auto-generated
        on first access) and is therefore intentionally skipped here so that
        callers cannot overwrite or clear it.
        """
        now = dt.datetime.now()
        for key, value in config.model_dump(mode="json").items():
            if key == "library_id":
                # Immutable once created — only get() is allowed to write it.
                continue
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
