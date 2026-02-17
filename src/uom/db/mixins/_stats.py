"""Aggregation / statistics mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from uom.db.dto import Media
from uom.db.helpers import to_media
from uom.db.models import MediaModel, MetadataModel


class StatsMixin:
    objects: peewee_aio.Manager

    async def total_size(self) -> int:
        return (
            await self.objects.fetchval(
                MediaModel.select(fn.SUM(MediaModel.file_size)).where(
                    MediaModel.deleted_at.is_null()
                )
            )
        ) or 0

    async def type_distribution(self) -> dict[str, int]:
        rows = await self.objects.fetchall(
            MediaModel.select(MediaModel.media_type, fn.COUNT(MediaModel.id).alias("cnt"))
            .where(MediaModel.deleted_at.is_null())
            .group_by(MediaModel.media_type)
            .dicts()
        )
        return {r["media_type"]: r["cnt"] for r in rows}

    async def cameras(self) -> list[dict[str, Any]]:
        rows = await self.objects.fetchall(
            MetadataModel.select(
                MetadataModel.camera_make,
                MetadataModel.camera_model,
                fn.COUNT(MetadataModel.id).alias("cnt"),
            )
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                ((MetadataModel.camera_make != "") | (MetadataModel.camera_model != ""))
                & MediaModel.deleted_at.is_null()
            )
            .group_by(MetadataModel.camera_make, MetadataModel.camera_model)
            .order_by(fn.COUNT(MetadataModel.id).desc())
            .dicts()
        )
        return [
            {"make": r["camera_make"], "model": r["camera_model"], "count": r["cnt"]} for r in rows
        ]

    async def timeline(self) -> list[dict[str, Any]]:
        from peewee import SQL

        rows = await self.objects.fetchall(
            MetadataModel.select(
                fn.DATE(MetadataModel.date_taken).alias("dt"),
                fn.COUNT(MetadataModel.id).alias("cnt"),
            )
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(MetadataModel.date_taken.is_null(False) & MediaModel.deleted_at.is_null())
            .group_by(SQL("dt"))
            .order_by(SQL("dt DESC"))
            .dicts()
        )
        return [{"date": str(r["dt"])[:10], "count": r["cnt"]} for r in rows if r["dt"]]

    async def get_random(self, count: int = 20, media_type: str | None = None) -> list[Media]:
        q = MediaModel.select().where(MediaModel.deleted_at.is_null())
        if media_type:
            q = q.where(MediaModel.media_type == media_type)
        return [
            to_media(m) for m in await self.objects.fetchall(q.order_by(fn.Random()).limit(count))
        ]

    async def geo_media(self, limit: int = 2000) -> list[dict[str, Any]]:
        rows = await self.objects.fetchall(
            MediaModel.select(
                MediaModel.id,
                MediaModel.filename,
                MediaModel.media_type,
                MetadataModel.gps_lat,
                MetadataModel.gps_lon,
                MetadataModel.date_taken,
                MetadataModel.location_city,
            )
            .join(MetadataModel, on=(MediaModel.id == MetadataModel.media))
            .where(
                MetadataModel.gps_lat.is_null(False)
                & MetadataModel.gps_lon.is_null(False)
                & MediaModel.deleted_at.is_null()
            )
            .order_by(MetadataModel.date_taken.desc())
            .limit(limit)
            .dicts()
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            d = r["date_taken"]
            ds = (
                d.strftime("%Y-%m-%d")
                if d and hasattr(d, "strftime")
                else (str(d)[:10] if d else None)
            )
            out.append(
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "media_type": r["media_type"],
                    "lat": r["gps_lat"],
                    "lon": r["gps_lon"],
                    "date": ds,
                    "city": r.get("location_city") or None,
                }
            )
        return out
