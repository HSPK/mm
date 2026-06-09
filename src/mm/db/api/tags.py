"""Ratings & tags database API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import peewee

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from mm.db.api._source import DbApi
from mm.db.dto import Tag
from mm.db.helpers import to_tag
from mm.db.models import MediaModel, MediaTagModel, TagModel, TagSource
from mm.utils.text import normalise_tag


class TagsApi(DbApi):
    objects: peewee_aio.Manager

    async def list(self) -> list[Tag]:
        return [
            to_tag(row)
            for row in await self.objects.fetchall(TagModel.select().order_by(TagModel.name))
        ]

    async def get_or_create(self, name: str, source: TagSource = TagSource.MANUAL) -> Tag:
        name = normalise_tag(name)
        try:
            t = await self.objects.get(TagModel, name=name)
        except TagModel.DoesNotExist:
            t = await self.objects.create(TagModel, name=name, source=source.value)
        return to_tag(t)

    async def get_by_name(self, name: str) -> Tag | None:
        name = normalise_tag(name)
        try:
            return to_tag(await self.objects.get(TagModel, name=name))
        except TagModel.DoesNotExist:
            return None

    async def add_media(self, media_id: int, tag_id: int, confidence: float = 1.0) -> None:
        try:
            await self.objects.create(
                MediaTagModel, media=media_id, tag=tag_id, confidence=confidence
            )
        except peewee.IntegrityError:
            pass

    async def remove_media(self, media_id: int, tag_id: int) -> None:
        await self.objects.execute(
            MediaTagModel.delete().where(
                (MediaTagModel.media == media_id) & (MediaTagModel.tag == tag_id)
            )
        )

    async def bulk_add(self, media_ids: list[int], tag_names: list[str]) -> int:
        """Bulk-tag many media with many tags. Was O(M*N) round-trips
        (one INSERT per (media, tag) pair plus per-name get_or_create);
        now uses 2 SELECTs + at most 2 INSERTs total regardless of size."""
        if not media_ids or not tag_names:
            return 0

        names = list({normalise_tag(n) for n in tag_names if n})
        if not names:
            return 0

        # Single SELECT for existing tags
        existing = {
            t.name: t
            for t in await self.objects.fetchall(
                TagModel.select().where(TagModel.name.in_(names))
            )
        }
        # Single INSERT for missing tags
        missing = [n for n in names if n not in existing]
        if missing:
            await self.objects.execute(
                TagModel.insert_many(
                    [{"name": n, "source": TagSource.MANUAL.value} for n in missing]
                ).on_conflict_ignore()
            )
            for t in await self.objects.fetchall(
                TagModel.select().where(TagModel.name.in_(missing))
            ):
                existing[t.name] = t

        tag_ids = [t.id for t in existing.values()]

        # Count pre-existing pairs so the caller knows how many were really added
        before = await self.objects.count(
            MediaTagModel.select().where(
                MediaTagModel.media.in_(media_ids)
                & MediaTagModel.tag.in_(tag_ids)
            )
        )
        # Single INSERT for the M*N cross product
        rows = [{"media": mid, "tag": tid} for mid in media_ids for tid in tag_ids]
        try:
            await self.objects.execute(
                MediaTagModel.insert_many(rows).on_conflict_ignore()
            )
        except peewee.IntegrityError:
            # Fallback for backends without ON CONFLICT
            for mid in media_ids:
                for tid in tag_ids:
                    try:
                        await self.objects.create(MediaTagModel, media=mid, tag=tid)
                    except peewee.IntegrityError:
                        pass

        after = await self.objects.count(
            MediaTagModel.select().where(
                MediaTagModel.media.in_(media_ids)
                & MediaTagModel.tag.in_(tag_ids)
            )
        )
        return max(0, after - before)

    async def bulk_remove(self, media_ids: list[int], tag_names: list[str]) -> int:
        tags = [await self.get_by_name(n) for n in tag_names]
        tag_ids = [t.id for t in tags if t and t.id]
        if not tag_ids:
            return 0
        removed = await self.objects.execute(
            MediaTagModel.delete().where(
                MediaTagModel.media.in_(media_ids) & MediaTagModel.tag.in_(tag_ids)
            )
        )
        await self.delete_orphans()
        return removed

    async def stats(self) -> list[tuple[int, str, int]]:
        rows = await self.objects.fetchall(
            TagModel.select(TagModel.id, TagModel.name, fn.COUNT(MediaTagModel.media).alias("cnt"))
            .join(MediaTagModel, peewee.JOIN.LEFT_OUTER)
            .group_by(TagModel.id, TagModel.name)
            .order_by(fn.COUNT(MediaTagModel.media).desc())
        )
        return [(r.id, r.name, r.cnt) for r in rows]

    async def rename(self, tag_id: int, new_name: str) -> None:
        await self.objects.execute(
            TagModel.update(name=normalise_tag(new_name)).where(TagModel.id == tag_id)
        )

    async def delete(self, tag_id: int) -> None:
        await self.objects.execute(TagModel.delete().where(TagModel.id == tag_id))

    async def delete_orphans(self) -> int:
        sub = MediaTagModel.select(MediaTagModel.tag).distinct()
        return await self.objects.execute(TagModel.delete().where(TagModel.id.not_in(sub)))

    async def delete_orphan_links(self) -> int:
        valid = MediaModel.select(MediaModel.id)
        return await self.objects.execute(
            MediaTagModel.delete().where(MediaTagModel.media.not_in(valid))
        )

    async def for_media(self, media_id: int) -> list[tuple[Tag, float]]:
        rows = await self.objects.fetchall(
            MediaTagModel.select(MediaTagModel, TagModel)
            .join(TagModel)
            .where(MediaTagModel.media == media_id)
        )
        return [(to_tag(r.tag), r.confidence) for r in rows]

    async def media_ids(self, tag_names: list[str], match_all: bool = True) -> list[int]:
        if not tag_names:
            return []
        names = [normalise_tag(name) for name in tag_names]
        q = (
            MediaTagModel.select(MediaTagModel.media)
            .join(TagModel, on=(MediaTagModel.tag == TagModel.id))
            .where(TagModel.name.in_(names))
        )
        if match_all:
            q = q.group_by(MediaTagModel.media).having(
                fn.COUNT(fn.DISTINCT(TagModel.id)) == len(names)
            )
        else:
            q = q.distinct()
        rows = await self.objects.fetchall(q)
        return [row.media_id for row in rows]
