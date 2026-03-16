"""Library config mixin — key-value settings stored in the DB."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from uom.config import DEFAULT_IMPORT_TEMPLATE
from uom.db.models import LibraryConfigModel

# Well-known config keys
KEY_IMPORT_TEMPLATE = "import_template"


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
        try:
            row = await self.objects.get(LibraryConfigModel, key=key)
            row.value = value
            row.updated_at = dt.datetime.now()
            await self.objects.update(row)
        except LibraryConfigModel.DoesNotExist:
            await self.objects.create(
                LibraryConfigModel,
                key=key,
                value=value,
                updated_at=dt.datetime.now(),
            )

    async def get_all_config(self) -> dict[str, str]:
        """Return all config key-value pairs."""
        rows = await self.objects.fetchall(LibraryConfigModel.select())
        return {r.key: r.value for r in rows}

    # ── Convenience helpers ───────────────────────────────

    async def get_import_template(self) -> str:
        """Return the stored import template, or the default."""
        return await self.get_config(KEY_IMPORT_TEMPLATE, DEFAULT_IMPORT_TEMPLATE)

    async def set_import_template(self, template: str) -> None:
        """Store the import template."""
        await self.set_config(KEY_IMPORT_TEMPLATE, template)
