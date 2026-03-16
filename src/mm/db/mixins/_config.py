"""Library config mixin — key-value settings stored in the DB."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from mm.db.models import LibraryConfigModel

# Well-known config keys
KEY_IMPORT_TEMPLATE = "import_template"
KEY_LIBRARY_NAME = "library_name"
KEY_LIBRARY_ROOT = "library_root"


class ConfigMixin:
    objects: peewee_aio.Manager

    # ── Low-level get / set ───────────────────────────────

    async def get_config(self, key: str, default: str = "") -> str:
        """Return the value for *key*, or *default* if not set."""
        try:
            row = await self.objects.get(LibraryConfigModel, key=key)
            return row.value
        except LibraryConfigModel.DoesNotExist:
            return default

    async def set_config(self, key: str, value: str) -> None:
        """Insert or update a config key."""
        now = dt.datetime.now()
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

    async def get_all_config(self) -> dict[str, str]:
        """Return all config key-value pairs."""
        rows = await self.objects.fetchall(LibraryConfigModel.select())
        return {r.key: r.value for r in rows}
