"""Media CRUD & query mixin."""

from __future__ import annotations

import datetime as dt
import math
from typing import TYPE_CHECKING

import peewee

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from uom.db.dto import Media
from uom.db.helpers import to_media
from uom.db.models import MediaModel, MediaTagModel, MetadataModel, TagModel


class MediaMixin:
    objects: peewee_aio.Manager

    # ── CRUD ──────────────────────────────────────────────

    async def get_total_media_count(self) -> int:
        return await self.objects.count(MediaModel.select().where(MediaModel.deleted_at.is_null()))

    async def get_media_by_id(self, media_id: int) -> Media | None:
        try:
            return to_media(await self.objects.get(MediaModel, id=media_id))
        except MediaModel.DoesNotExist:
            return None

    async def delete_media(self, media_id: int) -> bool:
        return (
            await self.objects.execute(MediaModel.delete().where(MediaModel.id == media_id))
        ) > 0

    async def soft_delete_media(self, media_id: int) -> bool:
        return (
            await self.objects.execute(
                MediaModel.update(deleted_at=dt.datetime.now()).where(
                    (MediaModel.id == media_id) & MediaModel.deleted_at.is_null()
                )
            )
        ) > 0

    async def restore_media(self, media_id: int) -> bool:
        return (
            await self.objects.execute(
                MediaModel.update(deleted_at=None).where(
                    (MediaModel.id == media_id) & MediaModel.deleted_at.is_null(False)
                )
            )
        ) > 0

    async def batch_soft_delete(self, media_ids: list[int]) -> int:
        return await self.objects.execute(
            MediaModel.update(deleted_at=dt.datetime.now()).where(
                MediaModel.id.in_(media_ids) & MediaModel.deleted_at.is_null()
            )
        )

    async def list_trash(self) -> list[Media]:
        return [
            to_media(m)
            for m in await self.objects.fetchall(
                MediaModel.select()
                .where(MediaModel.deleted_at.is_null(False))
                .order_by(MediaModel.deleted_at.desc())
            )
        ]

    async def empty_trash(self) -> int:
        return await self.objects.execute(
            MediaModel.delete().where(MediaModel.deleted_at.is_null(False))
        )

    async def purge_old_trash(self, days: int = 30) -> int:
        cutoff = dt.datetime.now() - dt.timedelta(days=days)
        return await self.objects.execute(
            MediaModel.delete().where(
                MediaModel.deleted_at.is_null(False) & (MediaModel.deleted_at < cutoff)
            )
        )

    # ── Query ─────────────────────────────────────────────

    async def query_media(
        self,
        page: int = 1,
        per_page: int = 60,
        media_type: str | None = None,
        tag_names: list[str] | None = None,
        camera: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        date_ranges: list[list[str]] | None = None,
        sort: str = "date_taken",
        order: str = "desc",
        search: str | None = None,
        min_rating: int | None = None,
        favorites_only: bool = False,
        lat: float | None = None,
        lon: float | None = None,
        radius: float | None = None,
        has_location: bool = False,
        no_date: bool = False,
        deleted: bool = False,
    ) -> tuple[list[Media], int]:
        need_meta = bool(
            camera
            or date_from
            or date_to
            or date_ranges
            or lat
            or lon
            or sort == "date_taken"
            or has_location
        )

        q = MediaModel.select().where(
            MediaModel.deleted_at.is_null(False) if deleted else MediaModel.deleted_at.is_null()
        )
        if need_meta:
            q = q.join(
                MetadataModel,
                on=(MediaModel.id == MetadataModel.media),
                join_type=peewee.JOIN.LEFT_OUTER,
            )

        # -- Content filters --
        if media_type:
            q = q.where(MediaModel.media_type == media_type)
        if search:
            tag_sub = (
                MediaTagModel.select(MediaTagModel.media)
                .join(TagModel)
                .where(TagModel.name.contains(search))
            )
            q = q.where(
                MediaModel.filename.contains(search)
                | MediaModel.path.contains(search)
                | MediaModel.id.in_(tag_sub)
            )
        if min_rating and min_rating > 0:
            q = q.where(MediaModel.rating >= min_rating)
        if favorites_only:
            q = q.where(MediaModel.rating >= 4)

        # -- Metadata filters --
        if camera:
            q = q.where(
                MetadataModel.camera_make.contains(camera)
                | MetadataModel.camera_model.contains(camera)
            )
        if no_date:
            has_date_sub = MetadataModel.select(MetadataModel.media).where(
                MetadataModel.date_taken.is_null(False)
            )
            q = q.where(MediaModel.id.not_in(has_date_sub))
        if date_from:
            q = q.where(MetadataModel.date_taken >= date_from)
        if date_to:
            q = q.where(MetadataModel.date_taken <= f"{date_to} 23:59:59")
        if date_ranges:
            cond = None
            for r in date_ranges:
                if len(r) >= 2:
                    c = (MetadataModel.date_taken >= r[0]) & (
                        MetadataModel.date_taken <= f"{r[1]} 23:59:59"
                    )
                    cond = c if cond is None else (cond | c)
            if cond is not None:
                q = q.where(cond)
        if has_location:
            q = q.where(MetadataModel.gps_lat.is_null(False) & MetadataModel.gps_lon.is_null(False))
        if lat is not None and lon is not None and radius is not None:
            d_lat = radius / 111.32
            clat = max(-89.9, min(89.9, lat))
            d_lon = radius / (111.32 * math.cos(math.radians(clat)))
            q = q.where(
                (MetadataModel.gps_lat.between(lat - d_lat, lat + d_lat))
                & (MetadataModel.gps_lon.between(lon - d_lon, lon + d_lon))
            )

        # -- Tag filters --
        if tag_names:
            sub = (
                MediaTagModel.select(MediaTagModel.media)
                .join(TagModel)
                .where(TagModel.name.in_(tag_names))
                .group_by(MediaTagModel.media)
                .having(fn.COUNT(TagModel.id) == len(tag_names))
            )
            q = q.where(MediaModel.id.in_(sub))

        # -- Sort --
        sort_map = {
            "date_taken": MetadataModel.date_taken if need_meta else MediaModel.created_at,
            "filename": MediaModel.filename,
            "rating": MediaModel.rating,
            "size": MediaModel.file_size,
        }
        sf = sort_map.get(sort, MediaModel.created_at)
        q = q.order_by(sf.asc() if order == "asc" else sf.desc())

        total = await self.objects.count(q)
        results = await self.objects.fetchall(q.paginate(page, per_page))
        return [to_media(m) for m in results], total

    count_media = get_total_media_count  # alias for CLI compat
