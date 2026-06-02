"""Shared helpers used by both sync and async repositories."""

from __future__ import annotations

import hashlib
import secrets

from mm.db.dto import Media, Metadata, Tag, User
from mm.db.models import (
    MediaModel,
    MediaType,
    MetadataModel,
    TagModel,
    TagSource,
    UserModel,
)
from mm.utils.parsing import parse_datetime

# ── Password hashing ─────────────────────────────────────


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":")
    except ValueError:
        return False
    return (
        hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
        == h
    )


# ── ORM → DTO converters ────────────────────────────────


def to_media(row: MediaModel) -> Media:
    return Media(
        id=row.id,
        path=row.path,
        filename=row.filename,
        extension=row.extension,
        media_type=MediaType(row.media_type),
        file_size=row.file_size,
        file_hash=row.file_hash,
        rating=getattr(row, "rating", 0) or 0,
        created_at=row.created_at,
        modified_at=row.modified_at,
        scanned_at=row.scanned_at,
        deleted_at=getattr(row, "deleted_at", None),
    )


def to_metadata(row: MetadataModel) -> Metadata:
    dt_val = row.date_taken
    if dt_val and isinstance(dt_val, str):
        dt_val = parse_datetime(dt_val) or dt_val
    return Metadata(
        id=row.id,
        media_id=row.media_id,
        date_taken=dt_val,
        camera_make=row.camera_make or "",
        camera_model=row.camera_model or "",
        lens_model=row.lens_model or "",
        focal_length=row.focal_length,
        aperture=row.aperture,
        shutter_speed=row.shutter_speed or "",
        iso=row.iso,
        width=row.width,
        height=row.height,
        duration=row.duration,
        gps_lat=row.gps_lat,
        gps_lon=row.gps_lon,
        orientation=row.orientation,
        location_label=getattr(row, "location_label", None),
        location_country=getattr(row, "location_country", None),
        location_city=getattr(row, "location_city", None),
    )


def to_tag(row: TagModel) -> Tag:
    return Tag(
        id=row.id,
        name=row.name,
        source=TagSource(row.source),
        created_at=row.created_at,
    )


def to_user(row: UserModel) -> User:
    return User(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        is_admin=bool(row.is_admin),
        created_at=row.created_at,
    )
