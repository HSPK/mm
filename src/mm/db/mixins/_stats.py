"""Aggregation / statistics mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import peewee_aio

from peewee import SQL, fn

from mm.db.dto import Media
from mm.db.helpers import to_media
from mm.db.models import (
    AlbumModel,
    EmbeddingModel,
    MediaModel,
    MediaTagModel,
    MetadataModel,
    TagModel,
)


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
            MediaModel.select(
                MediaModel.media_type, fn.COUNT(MediaModel.id).alias("cnt")
            )
            .where(MediaModel.deleted_at.is_null())
            .group_by(MediaModel.media_type)
            .dicts()
        )
        return {r["media_type"]: r["cnt"] for r in rows}

    # ------------------------------------------------------------------
    # Detailed stats helpers
    # ------------------------------------------------------------------

    async def stats_overview(self) -> dict[str, Any]:
        """Return a comprehensive overview dict."""
        alive = MediaModel.deleted_at.is_null()

        total = await self.objects.count(MediaModel.select().where(alive))
        photo_cnt = await self.objects.count(
            MediaModel.select().where(alive & (MediaModel.media_type == "photo"))
        )
        video_cnt = await self.objects.count(
            MediaModel.select().where(alive & (MediaModel.media_type == "video"))
        )

        total_size = (
            await self.objects.fetchval(
                MediaModel.select(fn.SUM(MediaModel.file_size)).where(alive)
            )
        ) or 0
        photo_size = (
            await self.objects.fetchval(
                MediaModel.select(fn.SUM(MediaModel.file_size)).where(
                    alive & (MediaModel.media_type == "photo")
                )
            )
        ) or 0
        video_size = (
            await self.objects.fetchval(
                MediaModel.select(fn.SUM(MediaModel.file_size)).where(
                    alive & (MediaModel.media_type == "video")
                )
            )
        ) or 0

        # Date range
        earliest = await self.objects.fetchval(
            MetadataModel.select(fn.MIN(MetadataModel.date_taken))
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(MetadataModel.date_taken.is_null(False) & alive)
        )
        latest = await self.objects.fetchval(
            MetadataModel.select(fn.MAX(MetadataModel.date_taken))
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(MetadataModel.date_taken.is_null(False) & alive)
        )

        # Video total duration
        video_duration = (
            await self.objects.fetchval(
                MetadataModel.select(fn.SUM(MetadataModel.duration))
                .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
                .where(MetadataModel.duration.is_null(False) & alive)
            )
        ) or 0.0

        # Counts
        tag_count = await self.objects.count(TagModel.select())
        album_count = await self.objects.count(AlbumModel.select())
        embedding_count = await self.objects.count(EmbeddingModel.select())

        return {
            "total": total,
            "photos": photo_cnt,
            "videos": video_cnt,
            "total_size": total_size,
            "photo_size": photo_size,
            "video_size": video_size,
            "earliest": str(earliest)[:10] if earliest else None,
            "latest": str(latest)[:10] if latest else None,
            "video_duration": video_duration,
            "tags": tag_count,
            "albums": album_count,
            "embeddings": embedding_count,
        }

    async def stats_by_year(self) -> list[dict[str, Any]]:
        """Per-year breakdown: year, photos, videos, total, size."""
        alive = MediaModel.deleted_at.is_null()
        rows = await self.objects.fetchall(
            MediaModel.select(
                fn.strftime("%Y", MetadataModel.date_taken).alias("year"),
                fn.SUM((MediaModel.media_type == "photo").cast("int")).alias("photos"),
                fn.SUM((MediaModel.media_type == "video").cast("int")).alias("videos"),
                fn.COUNT(MediaModel.id).alias("total"),
                fn.SUM(MediaModel.file_size).alias("size"),
            )
            .join(MetadataModel, on=(MediaModel.id == MetadataModel.media))
            .where(alive & MetadataModel.date_taken.is_null(False))
            .group_by(SQL("year"))
            .order_by(SQL("year"))
            .dicts()
        )
        return [
            {
                "year": r["year"],
                "photos": r["photos"] or 0,
                "videos": r["videos"] or 0,
                "total": r["total"] or 0,
                "size": r["size"] or 0,
            }
            for r in rows
            if r["year"]
        ]

    async def stats_by_camera(self) -> list[dict[str, Any]]:
        """Per-camera breakdown: make, model, photos, videos, total, size."""
        alive = MediaModel.deleted_at.is_null()
        rows = await self.objects.fetchall(
            MetadataModel.select(
                MetadataModel.camera_make,
                MetadataModel.camera_model,
                fn.SUM((MediaModel.media_type == "photo").cast("int")).alias("photos"),
                fn.SUM((MediaModel.media_type == "video").cast("int")).alias("videos"),
                fn.COUNT(MetadataModel.id).alias("total"),
                fn.SUM(MediaModel.file_size).alias("size"),
            )
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                ((MetadataModel.camera_make != "") | (MetadataModel.camera_model != ""))
                & alive
            )
            .group_by(MetadataModel.camera_make, MetadataModel.camera_model)
            .order_by(fn.COUNT(MetadataModel.id).desc())
            .dicts()
        )
        return [
            {
                "camera": f"{r['camera_make']} {r['camera_model']}".strip(),
                "photos": r["photos"] or 0,
                "videos": r["videos"] or 0,
                "total": r["total"] or 0,
                "size": r["size"] or 0,
            }
            for r in rows
        ]

    async def stats_by_extension(self) -> list[dict[str, Any]]:
        """Per-extension breakdown."""
        alive = MediaModel.deleted_at.is_null()
        rows = await self.objects.fetchall(
            MediaModel.select(
                fn.LOWER(MediaModel.extension).alias("ext"),
                fn.COUNT(MediaModel.id).alias("cnt"),
                fn.SUM(MediaModel.file_size).alias("size"),
            )
            .where(alive)
            .group_by(SQL("ext"))
            .order_by(fn.COUNT(MediaModel.id).desc())
            .dicts()
        )
        return [
            {"ext": r["ext"], "count": r["cnt"], "size": r["size"] or 0} for r in rows
        ]

    async def stats_ratings(self) -> list[dict[str, int]]:
        """Rating distribution."""
        alive = MediaModel.deleted_at.is_null()
        rows = await self.objects.fetchall(
            MediaModel.select(
                MediaModel.rating,
                fn.COUNT(MediaModel.id).alias("cnt"),
            )
            .where(alive)
            .group_by(MediaModel.rating)
            .order_by(MediaModel.rating)
            .dicts()
        )
        return [{"rating": r["rating"], "count": r["cnt"]} for r in rows]

    async def stats_completeness(self) -> dict[str, int]:
        """Counts for metadata completeness: has/missing date, GPS, camera, embeddings."""
        alive = MediaModel.deleted_at.is_null()
        total = await self.objects.count(MediaModel.select().where(alive))

        has_date = await self.objects.count(
            MetadataModel.select()
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(MetadataModel.date_taken.is_null(False) & alive)
        )
        has_gps = await self.objects.count(
            MetadataModel.select()
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                MetadataModel.gps_lat.is_null(False)
                & MetadataModel.gps_lon.is_null(False)
                & alive
            )
        )
        has_location_label = await self.objects.count(
            MetadataModel.select()
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                MetadataModel.location_label.is_null(False)
                & (MetadataModel.location_label != "")
                & alive
            )
        )
        has_camera = await self.objects.count(
            MetadataModel.select()
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                ((MetadataModel.camera_make != "") | (MetadataModel.camera_model != ""))
                & alive
            )
        )
        has_embeddings = await self.objects.count(
            EmbeddingModel.select()
            .join(MediaModel, on=(EmbeddingModel.media == MediaModel.id))
            .where(alive)
        )
        has_tags = (
            await self.objects.fetchval(
                MediaTagModel.select(fn.COUNT(fn.DISTINCT(MediaTagModel.media)))
                .join(MediaModel, on=(MediaTagModel.media == MediaModel.id))
                .where(alive)
            )
            or 0
        )

        return {
            "total": total,
            "has_date": has_date,
            "missing_date": total - has_date,
            "has_gps": has_gps,
            "missing_gps": total - has_gps,
            "has_location_label": has_location_label,
            "missing_location_label": total - has_location_label,
            "has_camera": has_camera,
            "missing_camera": total - has_camera,
            "has_embeddings": has_embeddings,
            "missing_embeddings": total - has_embeddings,
            "has_tags": has_tags,
            "missing_tags": total - has_tags,
        }

    async def stats_top_tags(self, limit: int = 15) -> list[dict[str, Any]]:
        """Most-used tags."""
        rows = await self.objects.fetchall(
            TagModel.select(
                TagModel.name,
                TagModel.source,
                fn.COUNT(MediaTagModel.media).alias("cnt"),
            )
            .join(MediaTagModel, on=(TagModel.id == MediaTagModel.tag))
            .group_by(TagModel.id)
            .order_by(fn.COUNT(MediaTagModel.media).desc())
            .limit(limit)
            .dicts()
        )
        return [
            {"tag": r["name"], "source": r["source"], "count": r["cnt"]} for r in rows
        ]

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
            {"make": r["camera_make"], "model": r["camera_model"], "count": r["cnt"]}
            for r in rows
        ]

    async def timeline(self) -> list[dict[str, Any]]:
        from peewee import SQL

        rows = await self.objects.fetchall(
            MetadataModel.select(
                fn.DATE(MetadataModel.date_taken).alias("dt"),
                fn.COUNT(MetadataModel.id).alias("cnt"),
            )
            .join(MediaModel, on=(MetadataModel.media == MediaModel.id))
            .where(
                MetadataModel.date_taken.is_null(False)
                & MediaModel.deleted_at.is_null()
            )
            .group_by(SQL("dt"))
            .order_by(SQL("dt DESC"))
            .dicts()
        )
        return [{"date": str(r["dt"])[:10], "count": r["cnt"]} for r in rows if r["dt"]]

    async def get_random(
        self, count: int = 20, media_type: str | None = None
    ) -> list[Media]:
        q = MediaModel.select().where(MediaModel.deleted_at.is_null())
        if media_type:
            q = q.where(MediaModel.media_type == media_type)
        return [
            to_media(m)
            for m in await self.objects.fetchall(q.order_by(fn.Random()).limit(count))
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
