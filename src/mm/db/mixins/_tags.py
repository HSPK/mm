"""Ratings & tags mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

import peewee

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from uom.db.dto import Tag
from uom.db.helpers import normalise_tag, to_tag
from uom.db.models import MediaTagModel, TagModel, TagSource


class TagsMixin:
    objects: peewee_aio.Manager

    async def get_or_create_tag(self, name: str, source: TagSource = TagSource.MANUAL) -> Tag:
        name = normalise_tag(name)
        try:
            t = await self.objects.get(TagModel, name=name)
        except TagModel.DoesNotExist:
            t = await self.objects.create(TagModel, name=name, source=source.value)
        return to_tag(t)

    async def get_tag_by_name(self, name: str) -> Tag | None:
        name = normalise_tag(name)
        try:
            return to_tag(await self.objects.get(TagModel, name=name))
        except TagModel.DoesNotExist:
            return None

    async def add_media_tag(self, media_id: int, tag_id: int, confidence: float = 1.0) -> None:
        try:
            await self.objects.create(
                MediaTagModel, media=media_id, tag=tag_id, confidence=confidence
            )
        except peewee.IntegrityError:
            pass

    async def remove_media_tag(self, media_id: int, tag_id: int) -> None:
        await self.objects.execute(
            MediaTagModel.delete().where(
                (MediaTagModel.media == media_id) & (MediaTagModel.tag == tag_id)
            )
        )

    async def bulk_add_tags(self, media_ids: list[int], tag_names: list[str]) -> int:
        tags = [await self.get_or_create_tag(n) for n in tag_names]
        count = 0
        for mid in media_ids:
            for t in tags:
                try:
                    await self.objects.create(MediaTagModel, media=mid, tag=t.id)
                    count += 1
                except peewee.IntegrityError:
                    pass
        return count

    async def bulk_remove_tags(self, media_ids: list[int], tag_names: list[str]) -> int:
        tags = [await self.get_tag_by_name(n) for n in tag_names]
        tag_ids = [t.id for t in tags if t and t.id]
        if not tag_ids:
            return 0
        removed = await self.objects.execute(
            MediaTagModel.delete().where(
                MediaTagModel.media.in_(media_ids) & MediaTagModel.tag.in_(tag_ids)
            )
        )
        await self.delete_orphan_tags()
        return removed

    async def tag_stats(self) -> list[tuple[str, int]]:
        rows = await self.objects.fetchall(
            TagModel.select(TagModel.name, fn.COUNT(MediaTagModel.media).alias("cnt"))
            .join(MediaTagModel, peewee.JOIN.LEFT_OUTER)
            .group_by(TagModel.name)
            .order_by(fn.COUNT(MediaTagModel.media).desc())
        )
        return [(r.name, r.cnt) for r in rows]

    async def rename_tag(self, tag_id: int, new_name: str) -> None:
        await self.objects.execute(
            TagModel.update(name=normalise_tag(new_name)).where(TagModel.id == tag_id)
        )

    async def delete_tag(self, tag_id: int) -> None:
        await self.objects.execute(TagModel.delete().where(TagModel.id == tag_id))

    async def delete_orphan_tags(self) -> int:
        sub = MediaTagModel.select(MediaTagModel.tag).distinct()
        return await self.objects.execute(TagModel.delete().where(TagModel.id.not_in(sub)))

    async def tags_for_media(self, media_id: int) -> list[tuple[Tag, float]]:
        rows = await self.objects.fetchall(
            MediaTagModel.select(MediaTagModel, TagModel)
            .join(TagModel)
            .where(MediaTagModel.media == media_id)
        )
        return [(to_tag(r.tag), r.confidence) for r in rows]
