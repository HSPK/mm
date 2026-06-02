"""Media CRUD & query database API."""

from __future__ import annotations

import datetime as dt
import math
from typing import TYPE_CHECKING

import peewee

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from mm.db.api._source import DbApi
from mm.db.dto import Media
from mm.db.helpers import to_media
from mm.db.models import MediaModel, MediaTagModel, MetadataModel, TagModel


class MediaApi(DbApi):
    objects: peewee_aio.Manager

    # ── Ratings ───────────────────────────────────────────

    async def set_rating(self, media_id: int, rating: int) -> None:
        await self.objects.execute(
            MediaModel.update(rating=rating).where(MediaModel.id == media_id)
        )

    async def bulk_set_rating(self, media_ids: list[int], rating: int) -> int:
        return await self.objects.execute(
            MediaModel.update(rating=rating).where(MediaModel.id.in_(media_ids))
        )

    # ── CRUD ──────────────────────────────────────────────

    async def list(self) -> list[Media]:
        return [
            to_media(row)
            for row in await self.objects.fetchall(MediaModel.select().order_by(MediaModel.path))
        ]

    async def paths(self) -> list[tuple[int, str]]:
        rows = await self.objects.fetchall(
            MediaModel.select(MediaModel.id, MediaModel.path).order_by(MediaModel.path)
        )
        return [(row.id, row.path) for row in rows]

    async def existing_hashes(self, hashes: list[str]) -> set[str]:
        unique_hashes = list({digest for digest in hashes if digest})
        if not unique_hashes:
            return set()

        found: set[str] = set()
        batch_size = 900
        for i in range(0, len(unique_hashes), batch_size):
            batch = unique_hashes[i : i + batch_size]
            rows = await self.objects.fetchall(
                MediaModel.select(MediaModel.file_hash)
                .where(
                    MediaModel.file_hash.in_(batch),
                    MediaModel.deleted_at.is_null(),
                )
                .distinct()
            )
            found.update(row.file_hash for row in rows)
        return found

    async def by_path(self, path: str) -> Media | None:
        try:
            return to_media(await self.objects.get(MediaModel, path=path))
        except MediaModel.DoesNotExist:
            return None

    async def by_hash(self, file_hash: str) -> list[Media]:
        return [
            to_media(row)
            for row in await self.objects.fetchall(
                MediaModel.select().where(MediaModel.file_hash == file_hash)
            )
        ]

    async def update_path(self, media_id: int, path: str, filename: str, extension: str) -> int:
        return await self.objects.execute(
            MediaModel.update(path=path, filename=filename, extension=extension).where(
                MediaModel.id == media_id
            )
        )

    async def upsert(self, media: Media) -> int:
        try:
            row = await self.objects.get(MediaModel, path=media.path)
            await self.objects.execute(
                MediaModel.update(
                    file_size=media.file_size,
                    file_hash=media.file_hash,
                    modified_at=media.modified_at,
                    scanned_at=dt.datetime.now(),
                ).where(MediaModel.id == row.id)
            )
            return row.id
        except MediaModel.DoesNotExist:
            row = await self.objects.create(
                MediaModel,
                path=media.path,
                filename=media.filename,
                extension=media.extension,
                media_type=media.media_type.value,
                file_size=media.file_size,
                file_hash=media.file_hash,
                created_at=media.created_at,
                modified_at=media.modified_at,
                scanned_at=dt.datetime.now(),
            )
            return row.id

    async def delete_rows(self, media_ids: list[int], batch_size: int = 500) -> int:
        deleted = 0
        for i in range(0, len(media_ids), batch_size):
            chunk = media_ids[i : i + batch_size]
            deleted += await self.objects.execute(
                MediaModel.delete().where(MediaModel.id.in_(chunk))
            )
        return deleted

    async def count(self) -> int:
        return await self.objects.count(MediaModel.select().where(MediaModel.deleted_at.is_null()))

    async def get(self, media_id: int) -> Media | None:
        try:
            return to_media(await self.objects.get(MediaModel, id=media_id))
        except MediaModel.DoesNotExist:
            return None

    async def delete(self, media_id: int) -> bool:
        return (
            await self.objects.execute(MediaModel.delete().where(MediaModel.id == media_id))
        ) > 0

    async def soft_delete(self, media_id: int) -> bool:
        return (
            await self.objects.execute(
                MediaModel.update(deleted_at=dt.datetime.now()).where(
                    (MediaModel.id == media_id) & MediaModel.deleted_at.is_null()
                )
            )
        ) > 0

    async def restore(self, media_id: int) -> bool:
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

    async def query(
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
            or search
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
                | MetadataModel.location_label.contains(search)
                | MetadataModel.location_city.contains(search)
                | MetadataModel.location_country.contains(search)
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
