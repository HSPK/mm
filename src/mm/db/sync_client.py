"""Synchronous database client with typed API namespaces."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from mm.db.api import (
    AlbumsApi,
    LibraryConfigApi,
    MediaApi,
    MetadataApi,
    SmartAlbumsApi,
    StatsApi,
    TagsApi,
    UsersApi,
)
from mm.db.client import AsyncDBClient
from mm.db.dto import Media, Metadata, Tag, User
from mm.db.models import TagSource
from mm.library.settings import LibraryConfig

T = TypeVar("T")


class _SyncApi:
    def __init__(self, run: Callable[[Awaitable[T]], T]) -> None:
        self._run = run


class SyncUserApi(_SyncApi):
    def __init__(self, api: UsersApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def verify(self, username: str, password: str) -> User | None:
        return self._run(self._api.verify(username, password))

    def create(
        self,
        username: str,
        password: str,
        display_name: str = "",
        is_admin: bool = False,
    ) -> User:
        return self._run(self._api.create(username, password, display_name, is_admin))

    def get_by_token(self, token: str) -> User | None:
        return self._run(self._api.get_by_token(token))

    def get_by_username(self, username: str) -> User | None:
        return self._run(self._api.get_by_username(username))

    def generate_token(self, user_id: int) -> str:
        return self._run(self._api.generate_token(user_id))

    def invalidate(self, token: str) -> None:
        return self._run(self._api.invalidate(token))

    def change_password(self, user_id: int, new_password: str) -> None:
        return self._run(self._api.change_password(user_id, new_password))

    def count(self) -> int:
        return self._run(self._api.count())

    def list(self) -> list[User]:
        return self._run(self._api.list())

    def delete(self, user_id: int) -> None:
        return self._run(self._api.delete(user_id))


class SyncMediaApi(_SyncApi):
    def __init__(self, api: MediaApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def list(self) -> list[Media]:
        return self._run(self._api.list())

    def paths(self) -> list[tuple[int, str]]:
        return self._run(self._api.paths())

    def existing_hashes(self, hashes: list[str]) -> set[str]:
        return self._run(self._api.existing_hashes(hashes))

    def by_path(self, path: str) -> Media | None:
        return self._run(self._api.by_path(path))

    def by_hash(self, file_hash: str) -> list[Media]:
        return self._run(self._api.by_hash(file_hash))

    def update_path(self, media_id: int, path: str, filename: str, extension: str) -> int:
        return self._run(self._api.update_path(media_id, path, filename, extension))

    def upsert(self, media: Media) -> int:
        return self._run(self._api.upsert(media))

    def delete_rows(self, media_ids: list[int], batch_size: int = 500) -> int:
        return self._run(self._api.delete_rows(media_ids, batch_size=batch_size))

    def set_rating(self, media_id: int, rating: int) -> None:
        return self._run(self._api.set_rating(media_id, rating))

    def bulk_set_rating(self, media_ids: list[int], rating: int) -> int:
        return self._run(self._api.bulk_set_rating(media_ids, rating))

    def count(self) -> int:
        return self._run(self._api.count())

    def get(self, media_id: int) -> Media | None:
        return self._run(self._api.get(media_id))

    def delete(self, media_id: int) -> bool:
        return self._run(self._api.delete(media_id))

    def soft_delete(self, media_id: int) -> bool:
        return self._run(self._api.soft_delete(media_id))

    def restore(self, media_id: int) -> bool:
        return self._run(self._api.restore(media_id))

    def batch_soft_delete(self, media_ids: list[int]) -> int:
        return self._run(self._api.batch_soft_delete(media_ids))

    def list_trash(self) -> list[Media]:
        return self._run(self._api.list_trash())

    def empty_trash(self) -> int:
        return self._run(self._api.empty_trash())

    def purge_old_trash(self, days: int = 30) -> int:
        return self._run(self._api.purge_old_trash(days))

    def query(
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
        return self._run(
            self._api.query(
                page=page,
                per_page=per_page,
                media_type=media_type,
                tag_names=tag_names,
                camera=camera,
                date_from=date_from,
                date_to=date_to,
                date_ranges=date_ranges,
                sort=sort,
                order=order,
                search=search,
                min_rating=min_rating,
                favorites_only=favorites_only,
                lat=lat,
                lon=lon,
                radius=radius,
                has_location=has_location,
                no_date=no_date,
                deleted=deleted,
            )
        )


class SyncTagApi(_SyncApi):
    def __init__(self, api: TagsApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def get_or_create(self, name: str, source: TagSource = TagSource.MANUAL) -> Tag:
        return self._run(self._api.get_or_create(name, source))

    def list(self) -> list[Tag]:
        return self._run(self._api.list())

    def get_by_name(self, name: str) -> Tag | None:
        return self._run(self._api.get_by_name(name))

    def add_media(self, media_id: int, tag_id: int, confidence: float = 1.0) -> None:
        return self._run(self._api.add_media(media_id, tag_id, confidence))

    def remove_media(self, media_id: int, tag_id: int) -> None:
        return self._run(self._api.remove_media(media_id, tag_id))

    def bulk_add(self, media_ids: list[int], tag_names: list[str]) -> int:
        return self._run(self._api.bulk_add(media_ids, tag_names))

    def bulk_remove(self, media_ids: list[int], tag_names: list[str]) -> int:
        return self._run(self._api.bulk_remove(media_ids, tag_names))

    def stats(self) -> list[tuple[str, int]]:
        return self._run(self._api.stats())

    def rename(self, tag_id: int, new_name: str) -> None:
        return self._run(self._api.rename(tag_id, new_name))

    def delete(self, tag_id: int) -> None:
        return self._run(self._api.delete(tag_id))

    def delete_orphans(self) -> int:
        return self._run(self._api.delete_orphans())

    def delete_orphan_links(self) -> int:
        return self._run(self._api.delete_orphan_links())

    def for_media(self, media_id: int) -> list[tuple[Tag, float]]:
        return self._run(self._api.for_media(media_id))

    def media_ids(self, tag_names: list[str], match_all: bool = True) -> list[int]:
        return self._run(self._api.media_ids(tag_names, match_all=match_all))


class SyncMetadataApi(_SyncApi):
    def __init__(self, api: MetadataApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def get(self, media_id: int) -> Metadata | None:
        return self._run(self._api.get(media_id))

    def get_for_ids(self, media_ids: list[int]) -> dict[int, Metadata]:
        return self._run(self._api.get_for_ids(media_ids))

    def update(self, media_id: int, **kwargs: Any) -> Metadata | None:
        return self._run(self._api.update(media_id, **kwargs))

    def upsert(self, metadata: Metadata) -> int:
        return self._run(self._api.upsert(metadata))

    def delete_orphans(self) -> int:
        return self._run(self._api.delete_orphans())

    def needing_geo(self, force_reparse: bool = False) -> list[Metadata]:
        return self._run(self._api.needing_geo(force_reparse=force_reparse))

    def update_location(
        self,
        metadata_id: int,
        label: str,
        country: str | None = None,
        city: str | None = None,
    ) -> None:
        return self._run(self._api.update_location(metadata_id, label, country=country, city=city))


class SyncAlbumApi(_SyncApi):
    def __init__(self, api: AlbumsApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def create(self, name: str, description: str = "") -> dict[str, Any]:
        return self._run(self._api.create(name, description))

    def list(self) -> list[dict[str, Any]]:
        return self._run(self._api.list())

    def delete(self, album_id: int) -> bool:
        return self._run(self._api.delete(album_id))

    def rename(self, album_id: int, name: str) -> bool:
        return self._run(self._api.rename(album_id, name))

    def add_media(self, album_id: int, media_ids: list[int]) -> int:
        return self._run(self._api.add_media(album_id, media_ids))

    def remove_media(self, album_id: int, media_ids: list[int]) -> int:
        return self._run(self._api.remove_media(album_id, media_ids))

    def media_ids(self, album_id: int) -> list[int]:
        return self._run(self._api.media_ids(album_id))


class SyncSmartAlbumApi(_SyncApi):
    def __init__(self, api: SmartAlbumsApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def list(self) -> list[dict[str, Any]]:
        return self._run(self._api.list())

    def list_all(self) -> list[dict[str, Any]]:
        return self._run(self._api.list_all())

    def get(self, album_id: int) -> dict[str, Any] | None:
        return self._run(self._api.get(album_id))

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._run(self._api.create(data))

    def update(self, album_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        return self._run(self._api.update(album_id, data))

    def delete(self, album_id: int) -> bool:
        return self._run(self._api.delete(album_id))

    def toggle(self, album_id: int) -> dict[str, Any] | None:
        return self._run(self._api.toggle(album_id))

    def seed(self) -> int:
        return self._run(self._api.seed())

    def reset(self) -> int:
        return self._run(self._api.reset())


class SyncStatsApi(_SyncApi):
    def __init__(self, api: StatsApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def total_size(self) -> int:
        return self._run(self._api.total_size())

    def type_distribution(self) -> dict[str, int]:
        return self._run(self._api.type_distribution())

    def overview(self) -> dict[str, Any]:
        return self._run(self._api.overview())

    def by_year(self) -> list[dict[str, Any]]:
        return self._run(self._api.by_year())

    def by_camera(self) -> list[dict[str, Any]]:
        return self._run(self._api.by_camera())

    def by_extension(self) -> list[dict[str, Any]]:
        return self._run(self._api.by_extension())

    def ratings(self) -> list[dict[str, int]]:
        return self._run(self._api.ratings())

    def completeness(self) -> dict[str, int]:
        return self._run(self._api.completeness())

    def top_tags(self, limit: int = 15) -> list[dict[str, Any]]:
        return self._run(self._api.top_tags(limit))

    def cameras(self) -> list[dict[str, Any]]:
        return self._run(self._api.cameras())

    def timeline(self) -> list[dict[str, Any]]:
        return self._run(self._api.timeline())

    def random(self, count: int = 20, media_type: str | None = None) -> list[Media]:
        return self._run(self._api.random(count, media_type))

    def geo_media(self, limit: int = 2000) -> list[dict[str, Any]]:
        return self._run(self._api.geo_media(limit))


class SyncLibraryConfigApi(_SyncApi):
    def __init__(self, api: LibraryConfigApi, run: Callable[[Awaitable[T]], T]) -> None:
        super().__init__(run)
        self._api = api

    def get(self) -> LibraryConfig:
        return self._run(self._api.get())

    def set(self, config: LibraryConfig) -> None:
        return self._run(self._api.set(config))


class DBClient:
    """Synchronous database client with typed namespace APIs."""

    user: SyncUserApi
    media: SyncMediaApi
    tag: SyncTagApi
    metadata: SyncMetadataApi
    album: SyncAlbumApi
    smart_album: SyncSmartAlbumApi
    stats: SyncStatsApi
    library_config: SyncLibraryConfigApi

    def __init__(self, db_path: str | Path) -> None:
        self._loop = asyncio.new_event_loop()
        self._client = AsyncDBClient(db_path)
        self.db_path = self._client.db_path
        self._run(self._client.connect())
        self._run(self._client.init_db())

        self.user = SyncUserApi(self._client.user, self._run)
        self.media = SyncMediaApi(self._client.media, self._run)
        self.tag = SyncTagApi(self._client.tag, self._run)
        self.metadata = SyncMetadataApi(self._client.metadata, self._run)
        self.album = SyncAlbumApi(self._client.album, self._run)
        self.smart_album = SyncSmartAlbumApi(self._client.smart_album, self._run)
        self.stats = SyncStatsApi(self._client.stats, self._run)
        self.library_config = SyncLibraryConfigApi(self._client.library_config, self._run)

    def _run(self, awaitable: Awaitable[T]) -> T:
        return self._loop.run_until_complete(awaitable)

    def close(self) -> None:
        self._loop.close()
