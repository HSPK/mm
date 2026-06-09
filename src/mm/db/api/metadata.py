"""Metadata database API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import peewee_aio

from mm.db.api._source import DbApi
from mm.db.dto import Metadata
from mm.db.helpers import to_metadata
from mm.db.models import MediaModel, MetadataModel


class MetadataApi(DbApi):
    objects: peewee_aio.Manager

    async def get(self, media_id: int) -> Metadata | None:
        try:
            return to_metadata(await self.objects.get(MetadataModel, media=media_id))
        except MetadataModel.DoesNotExist:
            return None

    async def get_for_ids(self, media_ids: list[int]) -> dict[int, Metadata]:
        if not media_ids:
            return {}
        rows = await self.objects.fetchall(
            MetadataModel.select().where(MetadataModel.media << media_ids)
        )
        return {r.media_id: to_metadata(r) for r in rows}

    async def upsert(self, metadata: Metadata) -> int:
        fields = {
            "date_taken": metadata.date_taken,
            "camera_make": metadata.camera_make,
            "camera_model": metadata.camera_model,
            "lens_model": metadata.lens_model,
            "focal_length": metadata.focal_length,
            "aperture": metadata.aperture,
            "shutter_speed": metadata.shutter_speed,
            "iso": metadata.iso,
            "width": metadata.width,
            "height": metadata.height,
            "duration": metadata.duration,
            "gps_lat": metadata.gps_lat,
            "gps_lon": metadata.gps_lon,
            "orientation": metadata.orientation,
        }
        try:
            row = await self.objects.get(MetadataModel, media=metadata.media_id)
            await self.objects.execute(
                MetadataModel.update(**fields).where(MetadataModel.id == row.id)
            )
            return row.id
        except MetadataModel.DoesNotExist:
            row = await self.objects.create(MetadataModel, media=metadata.media_id, **fields)
            return row.id

    async def delete_orphans(self) -> int:
        valid = MediaModel.select(MediaModel.id)
        return await self.objects.execute(
            MetadataModel.delete().where(MetadataModel.media.not_in(valid))
        )

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

    async def update(self, media_id: int, **kwargs: Any) -> Metadata | None:
        updates = {k: v for k, v in kwargs.items() if k in self._METADATA_FIELDS}
        if not updates:
            return await self.get(media_id)
        try:
            md = await self.objects.get(MetadataModel, media=media_id)
            await self.objects.execute(
                MetadataModel.update(**updates).where(MetadataModel.id == md.id)
            )
            return await self.get(media_id)
        except MetadataModel.DoesNotExist:
            md = await self.objects.create(MetadataModel, media=media_id, **updates)
            return to_metadata(md)

    async def bulk_update(self, media_ids: list[int], **kwargs: Any) -> int:
        """Apply the same patch to many media's metadata rows in 2 queries
        (UPDATE existing + INSERT missing). Returns the number of media
        whose metadata row is now present and patched."""
        updates = {k: v for k, v in kwargs.items() if k in self._METADATA_FIELDS}
        if not updates or not media_ids:
            return 0
        # Step 1: update all existing rows in one statement
        await self.objects.execute(
            MetadataModel.update(**updates).where(MetadataModel.media.in_(media_ids))
        )
        # Step 2: discover which media still lack a metadata row
        existing_rows = await self.objects.fetchall(
            MetadataModel.select(MetadataModel.media).where(
                MetadataModel.media.in_(media_ids)
            )
        )
        existing_ids = {r.media_id for r in existing_rows}
        missing = [mid for mid in media_ids if mid not in existing_ids]
        # Step 3: bulk-insert new metadata rows for the gap
        if missing:
            await self.objects.execute(
                MetadataModel.insert_many(
                    [{"media": mid, **updates} for mid in missing]
                ).on_conflict_ignore()
            )
        return len(media_ids)

    async def needing_geo(self, force_reparse: bool = False) -> list[Metadata]:
        q = MetadataModel.select().where(
            MetadataModel.gps_lat.is_null(False)
            & MetadataModel.gps_lon.is_null(False)
            & ~((MetadataModel.gps_lat == 0.0) & (MetadataModel.gps_lon == 0.0))
        )
        if not force_reparse:
            q = q.where(MetadataModel.location_label.is_null())
        rows = await self.objects.fetchall(q)
        return [to_metadata(row) for row in rows]

    async def update_location(
        self,
        metadata_id: int,
        label: str,
        country: str | None = None,
        city: str | None = None,
    ) -> None:
        await self.objects.execute(
            MetadataModel.update(
                location_label=label,
                location_country=country,
                location_city=city,
            ).where(MetadataModel.id == metadata_id)
        )
