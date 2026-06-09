"""Album database API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import peewee
from peewee import fn

if TYPE_CHECKING:
    import peewee_aio

from mm.db.api._source import DbApi
from mm.db.models import AlbumMediaModel, AlbumModel


class AlbumsApi(DbApi):
    objects: peewee_aio.Manager

    async def create(self, name: str, description: str = "") -> dict[str, Any]:
        a = await self.objects.create(AlbumModel, name=name, description=description)
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "cover_media_id": None,
            "count": 0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    async def list(self) -> list[dict[str, Any]]:
        """All albums + media-counts in a single LEFT JOIN — no N+1."""
        rows = await self.objects.fetchall(
            AlbumModel.select(
                AlbumModel,
                fn.COUNT(AlbumMediaModel.media).alias("media_count"),
            )
            .join(
                AlbumMediaModel,
                peewee.JOIN.LEFT_OUTER,
                on=(AlbumMediaModel.album == AlbumModel.id),
            )
            .group_by(AlbumModel.id)
            .order_by(AlbumModel.created_at.desc())
        )
        return [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "cover_media_id": a.cover_media_id if a.cover_media_id else None,
                "count": getattr(a, "media_count", 0) or 0,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]

    async def delete(self, album_id: int) -> bool:
        return (
            await self.objects.execute(AlbumModel.delete().where(AlbumModel.id == album_id))
        ) > 0

    async def rename(self, album_id: int, name: str) -> bool:
        return (
            await self.objects.execute(
                AlbumModel.update(name=name).where(AlbumModel.id == album_id)
            )
        ) > 0

    async def add_media(self, album_id: int, media_ids: list[int]) -> int:
        """Bulk-insert with conflict skip — single statement instead of N
        round-trips. Returns the number of newly inserted rows."""
        if not media_ids:
            return 0
        # Count existing pairs so the caller knows how many were actually added.
        before = await self.objects.count(
            AlbumMediaModel.select().where(
                (AlbumMediaModel.album == album_id)
                & AlbumMediaModel.media.in_(media_ids)
            )
        )
        rows = [{"album": album_id, "media": mid} for mid in media_ids]
        try:
            await self.objects.execute(
                AlbumMediaModel.insert_many(rows).on_conflict_ignore()
            )
        except peewee.IntegrityError:
            # Fall back to one-at-a-time on backends without ON CONFLICT
            for mid in media_ids:
                try:
                    await self.objects.create(AlbumMediaModel, album=album_id, media=mid)
                except peewee.IntegrityError:
                    pass
        after = await self.objects.count(
            AlbumMediaModel.select().where(
                (AlbumMediaModel.album == album_id)
                & AlbumMediaModel.media.in_(media_ids)
            )
        )
        inserted = max(0, after - before)
        # Set cover if not yet set — single conditional UPDATE
        await self.objects.execute(
            AlbumModel.update(cover_media=media_ids[0])
            .where(
                (AlbumModel.id == album_id)
                & (
                    AlbumModel.cover_media_id.is_null()
                    | (AlbumModel.cover_media_id == 0)
                )
            )
        )
        return inserted

    async def remove_media(self, album_id: int, media_ids: list[int]) -> int:
        return await self.objects.execute(
            AlbumMediaModel.delete().where(
                (AlbumMediaModel.album == album_id) & AlbumMediaModel.media.in_(media_ids)
            )
        )

    async def media_ids(self, album_id: int) -> list[int]:
        rows = await self.objects.fetchall(
            AlbumMediaModel.select(AlbumMediaModel.media).where(AlbumMediaModel.album == album_id)
        )
        return [r.media_id for r in rows]
