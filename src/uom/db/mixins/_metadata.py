"""Metadata CRUD mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import peewee_aio

from uom.db.dto import Metadata
from uom.db.helpers import to_metadata
from uom.db.models import MetadataModel


class MetadataMixin:
    objects: peewee_aio.Manager

    async def get_metadata(self, media_id: int) -> Metadata | None:
        try:
            return to_metadata(await self.objects.get(MetadataModel, media=media_id))
        except MetadataModel.DoesNotExist:
            return None

    async def get_metadata_for_ids(self, media_ids: list[int]) -> dict[int, Metadata]:
        if not media_ids:
            return {}
        rows = await self.objects.fetchall(
            MetadataModel.select().where(MetadataModel.media << media_ids)
        )
        return {r.media_id: to_metadata(r) for r in rows}

    _METADATA_FIELDS = frozenset(
        {
            "date_taken",
            "gps_lat",
            "gps_lon",
            "location_label",
            "location_city",
            "location_country",
            "camera_make",
            "camera_model",
            "lens_model",
            "focal_length",
            "aperture",
            "shutter_speed",
            "iso",
            "orientation",
        }
    )

    async def update_metadata(self, media_id: int, **kwargs: Any) -> Metadata | None:
        updates = {k: v for k, v in kwargs.items() if k in self._METADATA_FIELDS}
        if not updates:
            return await self.get_metadata(media_id)
        try:
            md = await self.objects.get(MetadataModel, media=media_id)
            await self.objects.execute(
                MetadataModel.update(**updates).where(MetadataModel.id == md.id)
            )
            return await self.get_metadata(media_id)
        except MetadataModel.DoesNotExist:
            md = await self.objects.create(MetadataModel, media=media_id, **updates)
            return to_metadata(md)
