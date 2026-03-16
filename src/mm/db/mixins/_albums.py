"""Album CRUD mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import peewee

if TYPE_CHECKING:
    import peewee_aio

from mm.db.models import AlbumMediaModel, AlbumModel


class AlbumsMixin:
    objects: peewee_aio.Manager

    async def create_album(self, name: str, description: str = "") -> dict[str, Any]:
        a = await self.objects.create(AlbumModel, name=name, description=description)
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "cover_media_id": None,
            "count": 0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    async def list_albums(self) -> list[dict[str, Any]]:
        albums = await self.objects.fetchall(
            AlbumModel.select().order_by(AlbumModel.created_at.desc())
        )
        out = []
        for a in albums:
            count = await self.objects.count(
                AlbumMediaModel.select().where(AlbumMediaModel.album == a.id)
            )
            out.append(
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "cover_media_id": a.cover_media_id if a.cover_media_id else None,
                    "count": count,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
            )
        return out

    async def delete_album(self, album_id: int) -> bool:
        return (
            await self.objects.execute(
                AlbumModel.delete().where(AlbumModel.id == album_id)
            )
        ) > 0

    async def rename_album(self, album_id: int, name: str) -> bool:
        return (
            await self.objects.execute(
                AlbumModel.update(name=name).where(AlbumModel.id == album_id)
            )
        ) > 0

    async def add_media_to_album(self, album_id: int, media_ids: list[int]) -> int:
        count = 0
        for mid in media_ids:
            try:
                await self.objects.create(AlbumMediaModel, album=album_id, media=mid)
                count += 1
            except peewee.IntegrityError:
                pass
        try:
            a = await self.objects.get(AlbumModel, id=album_id)
            if not a.cover_media_id and media_ids:
                await self.objects.execute(
                    AlbumModel.update(cover_media=media_ids[0]).where(
                        AlbumModel.id == album_id
                    )
                )
        except AlbumModel.DoesNotExist:
            pass
        return count

    async def remove_media_from_album(self, album_id: int, media_ids: list[int]) -> int:
        return await self.objects.execute(
            AlbumMediaModel.delete().where(
                (AlbumMediaModel.album == album_id)
                & AlbumMediaModel.media.in_(media_ids)
            )
        )

    async def get_album_media_ids(self, album_id: int) -> list[int]:
        rows = await self.objects.fetchall(
            AlbumMediaModel.select(AlbumMediaModel.media).where(
                AlbumMediaModel.album == album_id
            )
        )
        return [r.media_id for r in rows]
