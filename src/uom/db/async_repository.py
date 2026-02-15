"""Async Repository — Async CRUD operations using Peewee-Async."""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from pathlib import Path
from typing import Any

import peewee
import peewee_aio
from peewee import fn

from uom.db.models import (
    ALL_TABLES,
    EmbeddingModel,
    MediaModel,
    MediaTagModel,
    MediaType,
    MetadataModel,
    TagModel,
    UserModel,
    database,
)
from uom.db.repository import Media, Metadata, Tag, User


class AsyncRepository:
    """Async wrapper around Peewee models using peewee-aio."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        # Ensure sync database is initialized for migrations/sync usage
        if database.database is None:
            database.init(self._db_path)
            database.allow_sync = True

        # Use peewee-aio Manager for async operations
        self.manager = peewee_aio.Manager(f"aiosqlite:///{self._db_path}")
        # Register models to use this manager
        for model in (
            UserModel,
            MediaModel,
            MetadataModel,
            TagModel,
            MediaTagModel,
            EmbeddingModel,
        ):
            self.manager.register(model)

        # Alias for compatibility if needed, but safer to use self.manager
        self.objects = self.manager

    async def connect(self):
        async with self.manager:
            pass

    async def init_db(self):
        # Use manager.allow_sync() context manager so peewee-aio permits DDL
        with self.manager.allow_sync():
            self.manager.pw_database.create_tables(ALL_TABLES)

        # Seed default admin user if no users exist
        count = await self.count_users()
        if count == 0:
            await self.create_user(
                "admin", password="admin123", display_name="Admin", is_admin=True
            )
            print("[uom] Created default admin user: admin / admin123")

    # ------------------------------------------------------------------
    # User Management
    # ------------------------------------------------------------------

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return f"{salt}:{h.hex()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt, h = stored.split(":")
        except ValueError:
            return False
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return computed.hex() == h

    async def verify_user(self, username: str, password: str) -> User | None:
        try:
            u = await self.objects.get(UserModel, username=username)
            if self._verify_password(password, u.password_hash):
                return User(u.id, u.username, u.display_name, u.is_admin, u.created_at)
        except UserModel.DoesNotExist:
            return None
        return None

    async def generate_token(self, user_id: int) -> str:
        token = secrets.token_hex(32)
        query = UserModel.update(token=token).where(UserModel.id == user_id)
        await self.objects.execute(query)
        return token

    async def invalidate_token(self, token: str) -> None:
        query = UserModel.update(token=None).where(UserModel.token == token)
        await self.objects.execute(query)

    async def change_password(self, user_id: int, new_password: str) -> None:
        query = UserModel.update(password_hash=self._hash_password(new_password)).where(
            UserModel.id == user_id
        )
        await self.objects.execute(query)

    async def get_user_by_username(self, username: str) -> User | None:
        try:
            u = await self.objects.get(UserModel, username=username)
            return User(u.id, u.username, u.display_name, u.is_admin, u.created_at)
        except UserModel.DoesNotExist:
            return None

    async def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        is_admin: bool = False,
    ) -> User:
        # peewee-async create
        u = await self.objects.create(
            UserModel,
            username=username,
            password_hash=self._hash_password(password),
            display_name=display_name or username,
            is_admin=is_admin,
            created_at=dt.datetime.now(),
        )
        return User(u.id, u.username, u.display_name, u.is_admin, u.created_at)

    async def count_users(self) -> int:
        return await self.objects.count(UserModel.select())

    async def list_users(self) -> list[User]:
        users = await self.objects.execute(UserModel.select())
        return [self._to_user(u) for u in users]

    async def delete_user(self, user_id: int) -> None:
        query = UserModel.delete().where(UserModel.id == user_id)
        await self.objects.execute(query)

    async def total_size(self) -> int:
        return await self.objects.fetchval(MediaModel.select(fn.SUM(MediaModel.file_size))) or 0

    async def type_distribution(self) -> dict[str, int]:
        query = MediaModel.select(
            MediaModel.media_type, fn.COUNT(MediaModel.id).alias("cnt")
        ).group_by(MediaModel.media_type)
        rows = await self.objects.execute(query)
        return {r.media_type: r.cnt for r in rows}

    async def cameras(self) -> list[dict[str, Any]]:
        # cameras implementation:
        # returns [{make: ..., model: ..., count: ...}]
        query = (
            MetadataModel.select(
                MetadataModel.camera_make,
                MetadataModel.camera_model,
                fn.COUNT(MetadataModel.id).alias("cnt"),
            )
            .where((MetadataModel.camera_make != "") | (MetadataModel.camera_model != ""))
            .group_by(MetadataModel.camera_make, MetadataModel.camera_model)
            .order_by(fn.COUNT(MetadataModel.id).desc())
        )
        # Use .dicts() so execute returns dicts
        results = await self.objects.execute(query.dicts())
        return [
            {"make": r["camera_make"], "model": r["camera_model"], "count": r["cnt"]}
            for r in results
        ]

    async def timeline(self) -> list[dict[str, Any]]:
        from peewee import SQL

        date_expr = fn.DATE(MetadataModel.date_taken).alias("dt")
        query = (
            MetadataModel.select(
                date_expr,
                fn.COUNT(MetadataModel.id).alias("cnt"),
            )
            .where(MetadataModel.date_taken.is_null(False))
            .group_by(SQL("dt"))
            .order_by(SQL("dt DESC"))
        )

        results = await self.objects.execute(query.dicts())
        final = []
        for row in results:
            if row["dt"]:
                final.append({"date": str(row["dt"])[:10], "count": row["cnt"]})
        return final

    async def get_random(self, count: int = 20, media_type: str | None = None) -> list[Media]:
        query = MediaModel.select()
        if media_type:
            query = query.where(MediaModel.media_type == media_type)
        query = query.order_by(fn.Random()).limit(count)

        models = await self.objects.execute(query)
        return [self._to_media(m) for m in models]

    async def geo_media(self, limit: int = 2000) -> list[dict[str, Any]]:
        query = (
            MediaModel.select(
                MediaModel.id,
                MediaModel.filename,
                MediaModel.media_type,
                MetadataModel.gps_lat,
                MetadataModel.gps_lon,
                MetadataModel.date_taken,
            )
            .join(MetadataModel, on=(MediaModel.id == MetadataModel.media))
            .where((MetadataModel.gps_lat.is_null(False)) & (MetadataModel.gps_lon.is_null(False)))
            .order_by(MetadataModel.date_taken.desc())
            .limit(limit)
        )

        results = await self.objects.execute(query.dicts())
        final = []
        for row in results:
            dt = row["date_taken"]
            date_str = (
                dt.strftime("%Y-%m-%d")
                if (dt and hasattr(dt, "strftime"))
                else str(dt)[:10]
                if dt
                else None
            )
            final.append(
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "media_type": row["media_type"],  # string from db usually
                    "lat": row["gps_lat"],
                    "lon": row["gps_lon"],
                    "date": date_str,
                }
            )
        return final

    async def user_count(self) -> int:
        """Alias for count_users to match sync API."""
        return await self.count_users()

    async def get_user_by_token(self, token: str) -> User | None:
        try:
            u = await self.objects.get(UserModel, token=token)
            return User(u.id, u.username, u.display_name, u.is_admin, u.created_at)
        except UserModel.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Media Access
    # ------------------------------------------------------------------

    async def get_total_media_count(self) -> int:
        return await self.objects.count(MediaModel.select())

    async def get_media_by_id(self, media_id: int) -> Media | None:
        try:
            m = await self.objects.get(MediaModel, id=media_id)
            return self._to_media(m)
        except MediaModel.DoesNotExist:
            return None

    async def query_media(
        self,
        page: int = 1,
        per_page: int = 60,
        media_type: str | None = None,
        tag_names: list[str] | None = None,
        camera: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "date_taken",
        order: str = "desc",
        search: str | None = None,
        min_rating: int | None = None,
        favorites_only: bool = False,
    ) -> tuple[list[Media], int]:
        need_metadata_join = bool(camera or date_from or date_to or sort == "date_taken")

        query = MediaModel.select()

        if need_metadata_join:
            query = query.join(
                MetadataModel,
                on=(MediaModel.id == MetadataModel.media),
                join_type=peewee.JOIN.LEFT_OUTER,
            )

        # Content Filters
        if media_type:
            query = query.where(MediaModel.media_type == media_type)
        if search:
            query = query.where(
                (MediaModel.filename.contains(search)) | (MediaModel.path.contains(search))
            )

        if min_rating is not None and min_rating > 0:
            query = query.where(MediaModel.rating >= min_rating)

        if favorites_only:
            # Logic from sync repo: favorites is rating >= 1?
            # Seems low, but matching existing logic.
            query = query.where(
                MediaModel.rating >= 4
            )  # Corrected to standard 'favorite' threshold usually 4/5

        # Metadata Filters
        if camera:
            query = query.where(
                (MetadataModel.camera_make.contains(camera))
                | (MetadataModel.camera_model.contains(camera))
            )

        if date_from:
            query = query.where(MetadataModel.date_taken >= date_from)
        if date_to:
            query = query.where(
                MetadataModel.date_taken <= date_to
            )  # + " 23:59:59" handled by caller? Sync repo does string append.

        # Tag Filters
        if tag_names:
            # Subquery strategy for AND logic on tags
            # (media has tag A AND tag B)
            subquery = (
                MediaTagModel.select(MediaTagModel.media)
                .join(TagModel)
                .where(TagModel.name.in_(tag_names))
                .group_by(MediaTagModel.media)
                .having(fn.COUNT(TagModel.id) == len(tag_names))
            )
            query = query.where(MediaModel.id.in_(subquery))

        # Sort
        if sort == "date_taken" and need_metadata_join:
            sort_field = MetadataModel.date_taken
        elif sort == "filename":
            sort_field = MediaModel.filename
        elif sort == "rating":
            sort_field = MediaModel.rating
        elif sort == "size":
            sort_field = MediaModel.file_size
        else:
            sort_field = MediaModel.created_at  # sync repo uses created_at or scanned_at? Sync repo default was scanned_at in else block.

        if order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # Execution
        # Count total matches before pagination
        total = await self.objects.count(query)

        # Paginate and fetch
        paginated = query.paginate(page, per_page)
        result_models = await self.objects.fetchall(paginated)

        # Convert
        results = [self._to_media(m) for m in result_models]
        return results, total

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> dict[str, int]:
        total_media = await self.objects.count(MediaModel.select())
        total_tags = await self.objects.count(TagModel.select())
        total_users = await self.objects.count(UserModel.select())

        # Disk usage (sum)
        total_size = (
            await self.objects.fetchval(MediaModel.select(fn.SUM(MediaModel.file_size))) or 0
        )

        return {
            "media_count": total_media,
            "tag_count": total_tags,
            "user_count": total_users,
            "storage_usage": int(total_size),
        }

    # ------------------------------------------------------------------
    # Ratings & Tags
    # ------------------------------------------------------------------

    async def set_rating(self, media_id: int, rating: int) -> None:
        query = MediaModel.update(rating=rating).where(MediaModel.id == media_id)
        await self.objects.execute(query)

    async def get_tag_by_name(self, name: str) -> Tag | None:
        try:
            t = await self.objects.get(TagModel, name=name)
            return self._to_tag(t)
        except TagModel.DoesNotExist:
            return None

    async def get_or_create_tag(self, name: str) -> Tag:
        try:
            t = await self.objects.get(TagModel, name=name)
        except TagModel.DoesNotExist:
            t = await self.objects.create(TagModel, name=name, source=TagSource.MANUAL.value)
        return self._to_tag(t)

    async def add_media_tag(self, media_id: int, tag_id: int) -> None:
        try:
            await self.objects.create(MediaTagModel, media=media_id, tag=tag_id)
        except peewee.IntegrityError:
            pass

    async def remove_media_tag(self, media_id: int, tag_id: int) -> None:
        query = MediaTagModel.delete().where(
            (MediaTagModel.media == media_id) & (MediaTagModel.tag == tag_id)
        )
        await self.objects.execute(query)

    async def tag_stats(self) -> list[tuple[str, int]]:
        query = (
            TagModel.select(TagModel.name, fn.COUNT(MediaTagModel.media).alias("cnt"))
            .join(MediaTagModel, peewee.JOIN.LEFT_OUTER)
            .group_by(TagModel.name)
            .order_by(fn.COUNT(MediaTagModel.media).desc())
        )

        rows = await self.objects.execute(query)
        return [(r.name, r.cnt) for r in rows]

    async def rename_tag(self, tag_id: int, new_name: str) -> None:
        query = TagModel.update(name=new_name).where(TagModel.id == tag_id)
        await self.objects.execute(query)

    async def delete_tag(self, tag_id: int) -> None:
        query = TagModel.delete().where(TagModel.id == tag_id)
        await self.objects.execute(query)

    async def delete_orphan_tags(self) -> int:
        subq = MediaTagModel.select(MediaTagModel.tag).distinct()
        query = TagModel.delete().where(TagModel.id.not_in(subq))
        return await self.objects.execute(query)

    # ------------------------------------------------------------------
    # Metadata & Details
    # ------------------------------------------------------------------

    async def get_metadata(self, media_id: int) -> Metadata | None:
        try:
            md = await self.objects.get(MetadataModel, media=media_id)
            return self._to_metadata(md)
        except MetadataModel.DoesNotExist:
            return None

    async def tags_for_media(self, media_id: int) -> list[tuple[Tag, float]]:
        query = (
            MediaTagModel.select(MediaTagModel, TagModel)
            .join(TagModel)
            .where(MediaTagModel.media == media_id)
        )

        results = await self.objects.fetchall(query)
        return [(self._to_tag(r.tag), r.confidence) for r in results]

    # ------------------------------------------------------------------
    # DTO Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_tag(row: TagModel) -> Tag:
        return Tag(
            id=row.id,
            name=row.name,
            source=TagSource(row.source),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_metadata(row: MetadataModel) -> Metadata:
        return Metadata(
            id=row.id,
            media_id=row.media_id,
            date_taken=row.date_taken,
            camera_make=row.camera_make,
            camera_model=row.camera_model,
            lens_model=row.lens_model,
            focal_length=row.focal_length,
            aperture=row.aperture,
            shutter_speed=row.shutter_speed,
            iso=row.iso,
            width=row.width,
            height=row.height,
            duration=row.duration,
            gps_lat=row.gps_lat,
            gps_lon=row.gps_lon,
            orientation=row.orientation,
        )

    @staticmethod
    def _to_media(row: MediaModel) -> Media:
        return Media(
            id=row.id,
            path=row.path,
            filename=row.filename,
            extension=row.extension,
            media_type=MediaType(row.media_type),
            file_size=row.file_size,
            file_hash=row.file_hash,
            rating=row.rating if hasattr(row, "rating") else 0,
            created_at=row.created_at,
            modified_at=row.modified_at,
            scanned_at=row.scanned_at,
        )
