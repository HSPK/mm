"""CLI-oriented methods mixin."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from peewee import fn

from mm.db.dto import Embedding, Media, Metadata, Tag
from mm.db.helpers import normalise_tag, to_embedding, to_media, to_metadata, to_tag
from mm.db.models import (
    EmbeddingModel,
    MediaModel,
    MediaTagModel,
    MetadataModel,
    TagModel,
)


class CliMixin:
    objects: peewee_aio.Manager

    async def all_media(self) -> list[Media]:
        return [
            to_media(r)
            for r in await self.objects.fetchall(MediaModel.select().order_by(MediaModel.path))
        ]

    async def all_tags(self) -> list[Tag]:
        return [
            to_tag(r)
            for r in await self.objects.fetchall(TagModel.select().order_by(TagModel.name))
        ]

    async def all_media_paths(self) -> list[tuple[int, str]]:
        rows = await self.objects.fetchall(
            MediaModel.select(MediaModel.id, MediaModel.path).order_by(MediaModel.path)
        )
        return [(r.id, r.path) for r in rows]

    async def find_duplicate_hashes(self) -> dict[str, list[Media]]:
        """Return groups of media that share the same file_hash."""
        # Find hashes that appear more than once
        dup_query = (
            MediaModel.select(MediaModel.file_hash)
            .where(MediaModel.file_hash != "", MediaModel.deleted_at.is_null())
            .group_by(MediaModel.file_hash)
            .having(fn.COUNT(MediaModel.id) > 1)
        )
        dup_hashes = [r.file_hash for r in await self.objects.fetchall(dup_query)]
        if not dup_hashes:
            return {}

        rows = await self.objects.fetchall(
            MediaModel.select()
            .where(MediaModel.file_hash.in_(dup_hashes))
            .order_by(MediaModel.file_hash, MediaModel.file_size.desc())
        )
        groups: dict[str, list[Media]] = {}
        for r in rows:
            groups.setdefault(r.file_hash, []).append(to_media(r))
        return groups

    async def hash_exists(self, file_hash: str) -> Media | None:
        """Return the first media with this hash, or None."""
        if not file_hash:
            return None
        try:
            row = await self.objects.get(
                MediaModel,
                MediaModel.file_hash == file_hash,
                MediaModel.deleted_at.is_null(),
            )
            return to_media(row)
        except MediaModel.DoesNotExist:
            return None

    async def hashes_exist(self, hashes: list[str]) -> set[str]:
        """Return the subset of *hashes* that already exist in the library."""
        if not hashes:
            return set()
        found: set[str] = set()
        # Query in batches of 500 to avoid SQLite variable limit
        batch_size = 500
        for i in range(0, len(hashes), batch_size):
            batch = hashes[i : i + batch_size]
            rows = await self.objects.fetchall(
                MediaModel.select(MediaModel.file_hash)
                .where(
                    MediaModel.file_hash.in_(batch),
                    MediaModel.deleted_at.is_null(),
                )
                .distinct()
            )
            found.update(r.file_hash for r in rows)
        return found

    async def all_embeddings(self) -> list[Embedding]:
        return [
            to_embedding(r)
            for r in await self.objects.fetchall(
                EmbeddingModel.select().order_by(EmbeddingModel.media)
            )
        ]

    async def get_media_by_path(self, path: str) -> Media | None:
        try:
            return to_media(await self.objects.get(MediaModel, path=path))
        except MediaModel.DoesNotExist:
            return None

    async def get_media_by_hash(self, file_hash: str) -> list[Media]:
        return [
            to_media(r)
            for r in await self.objects.fetchall(
                MediaModel.select().where(MediaModel.file_hash == file_hash)
            )
        ]

    async def upsert_media(self, m: Media) -> int:
        try:
            row = await self.objects.get(MediaModel, path=m.path)
            await self.objects.execute(
                MediaModel.update(
                    file_size=m.file_size,
                    file_hash=m.file_hash,
                    modified_at=m.modified_at,
                    scanned_at=dt.datetime.now(),
                ).where(MediaModel.id == row.id)
            )
            return row.id
        except MediaModel.DoesNotExist:
            row = await self.objects.create(
                MediaModel,
                path=m.path,
                filename=m.filename,
                extension=m.extension,
                media_type=m.media_type.value,
                file_size=m.file_size,
                file_hash=m.file_hash,
                created_at=m.created_at,
                modified_at=m.modified_at,
                scanned_at=dt.datetime.now(),
            )
            return row.id

    async def upsert_metadata(self, md: Metadata) -> int:
        fields = {
            "date_taken": md.date_taken,
            "camera_make": md.camera_make,
            "camera_model": md.camera_model,
            "lens_model": md.lens_model,
            "focal_length": md.focal_length,
            "aperture": md.aperture,
            "shutter_speed": md.shutter_speed,
            "iso": md.iso,
            "width": md.width,
            "height": md.height,
            "duration": md.duration,
            "gps_lat": md.gps_lat,
            "gps_lon": md.gps_lon,
            "orientation": md.orientation,
        }
        try:
            row = await self.objects.get(MetadataModel, media=md.media_id)
            await self.objects.execute(
                MetadataModel.update(**fields).where(MetadataModel.id == row.id)
            )
            return row.id
        except MetadataModel.DoesNotExist:
            row = await self.objects.create(MetadataModel, media=md.media_id, **fields)
            return row.id

    async def upsert_embedding(self, emb: Embedding) -> int:
        try:
            row = await self.objects.get(EmbeddingModel, media=emb.media_id)
            await self.objects.execute(
                EmbeddingModel.update(
                    vector=emb.vector, model=emb.model, created_at=dt.datetime.now()
                ).where(EmbeddingModel.id == row.id)
            )
            return row.id
        except EmbeddingModel.DoesNotExist:
            row = await self.objects.create(
                EmbeddingModel,
                media=emb.media_id,
                vector=emb.vector,
                model=emb.model,
            )
            return row.id

    async def media_without_embedding(self) -> list[Media]:
        sub = EmbeddingModel.select(EmbeddingModel.media)
        return [
            to_media(r)
            for r in await self.objects.fetchall(
                MediaModel.select().where(MediaModel.id.not_in(sub)).order_by(MediaModel.path)
            )
        ]

    async def media_ids_by_tags(self, tag_names: list[str], match_all: bool = True) -> list[int]:
        if not tag_names:
            return []
        names = [normalise_tag(n) for n in tag_names]
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
        return [r.media_id for r in rows]

    async def bulk_delete_media(self, media_ids: list[int], batch_size: int = 500) -> int:
        deleted = 0
        for i in range(0, len(media_ids), batch_size):
            chunk = media_ids[i : i + batch_size]
            deleted += await self.objects.execute(
                MediaModel.delete().where(MediaModel.id.in_(chunk))
            )
        return deleted

    async def delete_orphan_metadata(self) -> int:
        valid = MediaModel.select(MediaModel.id)
        return await self.objects.execute(
            MetadataModel.delete().where(MetadataModel.media.not_in(valid))
        )

    async def delete_orphan_media_tags(self) -> int:
        valid = MediaModel.select(MediaModel.id)
        return await self.objects.execute(
            MediaTagModel.delete().where(MediaTagModel.media.not_in(valid))
        )

    async def delete_orphan_embeddings(self) -> int:
        valid = MediaModel.select(MediaModel.id)
        return await self.objects.execute(
            EmbeddingModel.delete().where(EmbeddingModel.media.not_in(valid))
        )

    async def get_metadata_needing_geo_update(
        self,
        force_reparse: bool = False,
    ) -> list[Metadata]:
        q = MetadataModel.select().where(
            MetadataModel.gps_lat.is_null(False)
            & MetadataModel.gps_lon.is_null(False)
            & ~((MetadataModel.gps_lat == 0.0) & (MetadataModel.gps_lon == 0.0))
        )
        if not force_reparse:
            q = q.where(MetadataModel.location_label.is_null())
        rows = await self.objects.fetchall(q)
        return [to_metadata(r) for r in rows]

    async def update_location_label(
        self,
        metadata_id: int,
        label: str,
        country: str | None = None,
        city: str | None = None,
    ) -> None:
        await self.objects.execute(
            MetadataModel.update(
                location_label=label, location_country=country, location_city=city
            ).where(MetadataModel.id == metadata_id)
        )
