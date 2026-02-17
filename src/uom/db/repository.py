"""Repository — sync CRUD operations using Peewee ORM (for CLI tools)."""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

from peewee import JOIN, fn

from uom.db.dto import Embedding, Media, Metadata, Tag, User
from uom.db.helpers import (
    hash_password,
    normalise_tag,
    to_embedding,
    to_media,
    to_metadata,
    to_tag,
    to_user,
    verify_password,
)
from uom.db.models import (
    ALL_TABLES,
    EmbeddingModel,
    MediaModel,
    MediaTagModel,
    MetadataModel,
    TagModel,
    TagSource,
    UserModel,
    database,
)

# Re-export DTOs for backwards compatibility
__all__ = ["Media", "Metadata", "Tag", "Embedding", "User", "Repository"]


class Repository:
    """Sync Peewee-backed repository for UOM."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        # Ensure database is configured immediately for sync tools if needed,
        # but for async we rely on init()
        database.init(self._db_path)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        # For async, we don't strictly "connect" in the same way, but let's keep this
        # for compatibility with sync scripts if any remain.
        # But actually, peewee_async uses a pool.
        database.connect(reuse_if_open=True)
        # Also need to allow async loop attach? Usually peewee_async handles this on query.

    def close(self) -> None:
        if not database.is_closed():
            database.close()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Create tables if they don't exist, then apply lightweight migrations."""
        database.create_tables(ALL_TABLES, safe=True)
        self._migrate()

    def _migrate(self) -> None:
        """Apply schema migrations that create_tables(safe=True) cannot handle."""
        # Media Table
        cursor = database.execute_sql("PRAGMA table_info(media)")
        media_cols = {row[1] for row in cursor.fetchall()}
        if "rating" not in media_cols:
            database.execute_sql("ALTER TABLE media ADD COLUMN rating SMALLINT NOT NULL DEFAULT 0")

        # Metadata Table
        cursor = database.execute_sql("PRAGMA table_info(metadata)")
        meta_cols = {row[1] for row in cursor.fetchall()}
        if "location_label" not in meta_cols:
            database.execute_sql("ALTER TABLE metadata ADD COLUMN location_label VARCHAR(256)")
        if "location_country" not in meta_cols:
            database.execute_sql("ALTER TABLE metadata ADD COLUMN location_country VARCHAR(64)")
        if "location_city" not in meta_cols:
            database.execute_sql("ALTER TABLE metadata ADD COLUMN location_city VARCHAR(64)")

    # ------------------------------------------------------------------
    # Media CRUD
    # ------------------------------------------------------------------

    def upsert_media(self, m: Media) -> int:
        """Insert or update a media record.  Returns the row id."""
        row, created = MediaModel.get_or_create(
            path=m.path,
            defaults={
                "filename": m.filename,
                "extension": m.extension,
                "media_type": m.media_type.value,
                "file_size": m.file_size,
                "file_hash": m.file_hash,
                "created_at": m.created_at,
                "modified_at": m.modified_at,
                "scanned_at": dt.datetime.now(),
            },
        )
        if not created:
            row.file_size, row.file_hash = m.file_size, m.file_hash
            row.modified_at, row.scanned_at = m.modified_at, dt.datetime.now()
            row.save()
        return row.id

    def get_media_by_path(self, path: str) -> Media | None:
        try:
            return to_media(MediaModel.get(MediaModel.path == path))
        except MediaModel.DoesNotExist:
            return None

    def get_media_by_hash(self, file_hash: str) -> list[Media]:
        return [to_media(r) for r in MediaModel.select().where(MediaModel.file_hash == file_hash)]

    def get_media_by_id(self, media_id: int) -> Media | None:
        try:
            return to_media(MediaModel.get_by_id(media_id))
        except MediaModel.DoesNotExist:
            return None

    def count_media(self) -> int:
        return MediaModel.select().count()

    def total_size(self) -> int:
        result = MediaModel.select(fn.COALESCE(fn.SUM(MediaModel.file_size), 0)).scalar()
        return result or 0

    def type_distribution(self) -> dict[str, int]:
        query = MediaModel.select(
            MediaModel.media_type, fn.COUNT(MediaModel.id).alias("cnt")
        ).group_by(MediaModel.media_type)
        return {row.media_type: row.cnt for row in query}

    def all_media(self) -> list[Media]:
        return [to_media(r) for r in MediaModel.select().order_by(MediaModel.path)]

    def query_media(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
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
        lat: float | None = None,
        lon: float | None = None,
        radius: float | None = None,
    ) -> tuple[list[Media], int]:
        """Paginated media query with filters. Returns (items, total_count)."""
        need_metadata_join = any([camera, date_from, date_to, lat, lon, sort == "date_taken"])

        # Build base query — always select MediaModel columns only
        query = MediaModel.select(MediaModel)

        if need_metadata_join:
            query = query.join(
                MetadataModel,
                on=(MediaModel.id == MetadataModel.media),
                join_type=JOIN.LEFT_OUTER,
            ).switch(MediaModel)

        # --- filters ---
        if media_type:
            query = query.where(MediaModel.media_type == media_type)

        if search:
            # Also search in tag names
            tag_match_sub = (
                MediaTagModel.select(MediaTagModel.media)
                .join(TagModel, on=(MediaTagModel.tag == TagModel.id))
                .where(TagModel.name.contains(search))
            )
            query = query.where(
                (MediaModel.filename.contains(search)) | (MediaModel.id.in_(tag_match_sub))
            )

        if min_rating is not None and min_rating > 0:
            query = query.where(MediaModel.rating >= min_rating)

        if favorites_only:
            query = query.where(MediaModel.rating >= 1)

        if camera:
            # Camera filter: combined "make model" string.
            # Try matching make/model individually and via concatenation.
            cam_parts = camera.strip().split(None, 1)
            if len(cam_parts) == 2:
                query = query.where(
                    (
                        (MetadataModel.camera_make == cam_parts[0])
                        & (MetadataModel.camera_model == cam_parts[1])
                    )
                    | (MetadataModel.camera_make.contains(camera))
                    | (MetadataModel.camera_model.contains(camera))
                )
            else:
                query = query.where(
                    (MetadataModel.camera_make.contains(camera))
                    | (MetadataModel.camera_model.contains(camera))
                )
        if date_from:
            query = query.where(MetadataModel.date_taken >= date_from)
        if date_to:
            query = query.where(MetadataModel.date_taken <= date_to + " 23:59:59")

        if lat is not None and lon is not None and radius is not None:
            # Roughly 111km per degree
            d_lat = radius / 111.32
            # Handle lon near poles (cos -> 0); clip to safe range
            clat = max(-89.9, min(89.9, lat))
            d_lon = radius / (111.32 * math.cos(math.radians(clat)))
            query = query.where(
                (MetadataModel.gps_lat >= lat - d_lat)
                & (MetadataModel.gps_lat <= lat + d_lat)
                & (MetadataModel.gps_lon >= lon - d_lon)
                & (MetadataModel.gps_lon <= lon + d_lon)
            )

        if tag_names:
            names = [normalise_tag(n) for n in tag_names]
            media_ids_sub = (
                MediaTagModel.select(MediaTagModel.media)
                .join(TagModel, on=(MediaTagModel.tag == TagModel.id))
                .where(TagModel.name.in_(names))
                .group_by(MediaTagModel.media)
                .having(fn.COUNT(fn.DISTINCT(TagModel.id)) == len(names))
            )
            query = query.where(MediaModel.id.in_(media_ids_sub))

        # --- count ---
        if need_metadata_join:
            count_q = query.select(fn.COUNT(fn.DISTINCT(MediaModel.id)))
            total: int = count_q.scalar() or 0
        else:
            total = query.count()

        # --- sort ---
        if sort == "date_taken" and need_metadata_join:
            sort_col = MetadataModel.date_taken
        elif sort == "filename":
            sort_col = MediaModel.filename
        elif sort == "size":
            sort_col = MediaModel.file_size
        elif sort == "rating":
            sort_col = MediaModel.rating
        else:
            sort_col = MediaModel.scanned_at

        query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

        # --- paginate ---
        query = query.paginate(page, per_page)

        return [to_media(r) for r in query], total

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def set_rating(self, media_id: int, rating: int) -> None:
        """Set rating (0-5) for a media record."""
        rating = max(0, min(5, rating))
        MediaModel.update(rating=rating).where(MediaModel.id == media_id).execute()

    # ------------------------------------------------------------------
    # Timeline (group by date)
    # ------------------------------------------------------------------

    def timeline(self) -> list[dict]:
        """Return [{date: '2023-07-15', count: 42}, ...]."""
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
        results = []
        for row in query.dicts():
            if row["dt"]:
                results.append({"date": str(row["dt"])[:10], "count": row["cnt"]})
        return results

    # ------------------------------------------------------------------
    # Camera list
    # ------------------------------------------------------------------

    def cameras(self) -> list[dict]:
        """Return [{camera: 'Xiaomi 13', count: 120}, ...]."""
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
        results = []
        for row in query:
            cam = f"{row.camera_make} {row.camera_model}".strip()
            if cam:
                results.append({"camera": cam, "count": row.cnt})
        return results

    # ------------------------------------------------------------------
    # Random media
    # ------------------------------------------------------------------

    def random_media(self, count: int = 20, media_type: str | None = None) -> list[Media]:
        from peewee import SQL

        query = MediaModel.select().order_by(SQL("RANDOM()")).limit(count)
        if media_type:
            query = query.where(MediaModel.media_type == media_type)
        return [to_media(r) for r in query]

    def geo_media(self, limit: int = 2000) -> list[dict]:
        """Return media with GPS coordinates for map view."""
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
            .where(
                MetadataModel.gps_lat.is_null(False),
                MetadataModel.gps_lon.is_null(False),
            )
            .order_by(MetadataModel.date_taken.desc())
            .limit(limit)
            .dicts()
        )
        results = []
        for row in query:
            dt = row.get("date_taken")
            date_str = (
                (dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10])
                if dt
                else None
            )
            results.append(
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "media_type": row["media_type"].value
                    if hasattr(row["media_type"], "value")
                    else str(row["media_type"]),
                    "lat": row["gps_lat"],
                    "lon": row["gps_lon"],
                    "date": date_str,
                }
            )
        return results

    def media_without_embedding(self) -> list[Media]:
        subq = EmbeddingModel.select(EmbeddingModel.media)
        return [
            to_media(r)
            for r in MediaModel.select().where(MediaModel.id.not_in(subq)).order_by(MediaModel.path)
        ]

    def delete_media(self, media_id: int) -> None:
        MediaModel.delete_by_id(media_id)

    def all_media_paths(self) -> list[tuple[int, str]]:
        """Return (id, path) for every media row — lightweight query."""
        return [
            (row.id, row.path)
            for row in MediaModel.select(MediaModel.id, MediaModel.path).order_by(MediaModel.path)
        ]

    def bulk_delete_media(self, media_ids: list[int], batch_size: int = 500) -> int:
        """Delete media rows (+ cascaded children) in batches. Returns count deleted."""
        deleted = 0
        for i in range(0, len(media_ids), batch_size):
            chunk = media_ids[i : i + batch_size]
            # Cascade: metadata, media_tags, embeddings deleted by FK ON DELETE CASCADE
            deleted += MediaModel.delete().where(MediaModel.id.in_(chunk)).execute()
        return deleted

    def delete_orphan_tags(self) -> int:
        """Remove tags that are not associated with any media."""
        subq = MediaTagModel.select(MediaTagModel.tag).distinct()
        return TagModel.delete().where(TagModel.id.not_in(subq)).execute()

    def delete_orphan_metadata(self) -> int:
        """Remove metadata rows whose media no longer exists."""
        valid_media = MediaModel.select(MediaModel.id)
        return MetadataModel.delete().where(MetadataModel.media.not_in(valid_media)).execute()

    def delete_orphan_media_tags(self) -> int:
        """Remove media_tag rows whose media no longer exists."""
        valid_media = MediaModel.select(MediaModel.id)
        return MediaTagModel.delete().where(MediaTagModel.media.not_in(valid_media)).execute()

    def delete_orphan_embeddings(self) -> int:
        """Remove embedding rows whose media no longer exists."""
        valid_media = MediaModel.select(MediaModel.id)
        return EmbeddingModel.delete().where(EmbeddingModel.media.not_in(valid_media)).execute()

    # ------------------------------------------------------------------
    # Metadata CRUD
    # ------------------------------------------------------------------

    def upsert_metadata(self, md: Metadata) -> int:
        _fields = {
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
        row, created = MetadataModel.get_or_create(media=md.media_id, defaults=_fields)
        if not created:
            for k, v in _fields.items():
                setattr(row, k, v)
            row.save()
        return row.id

    def get_metadata(self, media_id: int) -> Metadata | None:
        try:
            return to_metadata(MetadataModel.get(MetadataModel.media == media_id))
        except MetadataModel.DoesNotExist:
            return None

    def get_metadata_needing_geo_update(self, force_reparse: bool = False) -> list[Metadata]:
        """
        Get metadata records that need location update.
        If force_reparse=False, only items with NO location_label (missing completely).
        If force_reparse=True, ALL items with valid GPS (re-geocode everything).
        """
        query = MetadataModel.select().where(
            MetadataModel.gps_lat.is_null(False),
            MetadataModel.gps_lon.is_null(False),
            ~((MetadataModel.gps_lat == 0.0) & (MetadataModel.gps_lon == 0.0)),
        )

        if not force_reparse:
            query = query.where(MetadataModel.location_label.is_null())

        return [to_metadata(m) for m in query]

    def update_location_label(
        self, metadata_id: int, label: str, country: str | None = None, city: str | None = None
    ) -> None:
        """Update location label for a metadata record."""
        MetadataModel.update(
            location_label=label, location_country=country, location_city=city
        ).where(MetadataModel.id == metadata_id).execute()

    # ------------------------------------------------------------------
    # Tag CRUD
    # ------------------------------------------------------------------

    def get_or_create_tag(self, name: str, source: TagSource = TagSource.MANUAL) -> Tag:
        name = normalise_tag(name)
        row, _ = TagModel.get_or_create(name=name, defaults={"source": source.value})
        return to_tag(row)

    def get_tag_by_name(self, name: str) -> Tag | None:
        name = normalise_tag(name)
        try:
            return to_tag(TagModel.get(TagModel.name == name))
        except TagModel.DoesNotExist:
            return None

    def all_tags(self) -> list[Tag]:
        return [to_tag(r) for r in TagModel.select().order_by(TagModel.name)]

    def tag_stats(self) -> list[tuple[str, int]]:
        query = (
            TagModel.select(TagModel.name, fn.COUNT(MediaTagModel.media).alias("cnt"))
            .join(MediaTagModel, on=(TagModel.id == MediaTagModel.tag), join_type=JOIN.LEFT_OUTER)
            .group_by(TagModel.id)
            .order_by(fn.COUNT(MediaTagModel.media).desc())
        )
        return [(row.name, row.cnt) for row in query]

    # ------------------------------------------------------------------
    # MediaTag CRUD
    # ------------------------------------------------------------------

    def add_media_tag(self, media_id: int, tag_id: int, confidence: float = 1.0) -> None:
        MediaTagModel.insert(
            media=media_id, tag=tag_id, confidence=confidence
        ).on_conflict_ignore().execute()

    def remove_media_tag(self, media_id: int, tag_id: int) -> None:
        MediaTagModel.delete().where(
            (MediaTagModel.media == media_id) & (MediaTagModel.tag == tag_id)
        ).execute()

    def tags_for_media(self, media_id: int) -> list[tuple[Tag, float]]:
        query = (
            TagModel.select(TagModel, MediaTagModel.confidence)
            .join(MediaTagModel, on=(TagModel.id == MediaTagModel.tag))
            .where(MediaTagModel.media == media_id)
            .order_by(TagModel.name)
        )
        return [(to_tag(row), row.mediatagmodel.confidence) for row in query]

    def media_ids_by_tags(self, tag_names: list[str], match_all: bool = True) -> list[int]:
        if not tag_names:
            return []
        names = [self._normalise_tag(n) for n in tag_names]
        query = (
            MediaTagModel.select(MediaTagModel.media)
            .join(TagModel, on=(MediaTagModel.tag == TagModel.id))
            .where(TagModel.name.in_(names))
        )
        if match_all:
            query = query.group_by(MediaTagModel.media).having(
                fn.COUNT(fn.DISTINCT(TagModel.id)) == len(names)
            )
        else:
            query = query.distinct()
        return [row.media_id for row in query]

    # ------------------------------------------------------------------
    # Embedding CRUD
    # ------------------------------------------------------------------

    def upsert_embedding(self, emb: Embedding) -> int:
        row, created = EmbeddingModel.get_or_create(
            media=emb.media_id,
            defaults={"vector": emb.vector, "model": emb.model},
        )
        if not created:
            row.vector, row.model = emb.vector, emb.model
            row.created_at = dt.datetime.now()
            row.save()
        return row.id

    def get_embedding(self, media_id: int) -> Embedding | None:
        try:
            return to_embedding(EmbeddingModel.get(EmbeddingModel.media == media_id))
        except EmbeddingModel.DoesNotExist:
            return None

    def all_embeddings(self) -> list[Embedding]:
        return [to_embedding(r) for r in EmbeddingModel.select().order_by(EmbeddingModel.media)]

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------

    _hash_password = staticmethod(hash_password)
    _verify_password = staticmethod(verify_password)

    def user_count(self) -> int:
        return UserModel.select().count()

    def create_user(
        self, username: str, password: str, display_name: str = "", is_admin: bool = False
    ) -> User:
        row = UserModel.create(
            username=username.strip().lower(),
            password_hash=hash_password(password),
            display_name=display_name or username,
            is_admin=1 if is_admin else 0,
        )
        return to_user(row)

    def verify_user(self, username: str, password: str) -> User | None:
        try:
            row = UserModel.get(UserModel.username == username.strip().lower())
        except UserModel.DoesNotExist:
            return None
        return to_user(row) if verify_password(password, row.password_hash) else None

    def generate_token(self, user_id: int) -> str:
        token = secrets.token_hex(32)
        UserModel.update(token=token).where(UserModel.id == user_id).execute()
        return token

    def get_user_by_token(self, token: str) -> User | None:
        try:
            return to_user(UserModel.get(UserModel.token == token))
        except UserModel.DoesNotExist:
            return None

    def invalidate_token(self, token: str) -> None:
        UserModel.update(token=None).where(UserModel.token == token).execute()

    def list_users(self) -> list[User]:
        return [to_user(r) for r in UserModel.select().order_by(UserModel.username)]

    def delete_user(self, user_id: int) -> None:
        UserModel.delete_by_id(user_id)

    def change_password(self, user_id: int, new_password: str) -> None:
        UserModel.update(password_hash=hash_password(new_password)).where(
            UserModel.id == user_id
        ).execute()

    # ------------------------------------------------------------------
    # Tag management (rename / delete)
    # ------------------------------------------------------------------

    def rename_tag(self, tag_id: int, new_name: str) -> None:
        TagModel.update(name=normalise_tag(new_name)).where(TagModel.id == tag_id).execute()

    def delete_tag(self, tag_id: int) -> None:
        MediaTagModel.delete().where(MediaTagModel.tag == tag_id).execute()
        TagModel.delete_by_id(tag_id)
