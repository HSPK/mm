from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBase


class LoginBody(PydanticBase):
    username: str
    password: str


class SetupBody(PydanticBase):
    username: str
    password: str
    display_name: str = ""


class CreateUserBody(PydanticBase):
    username: str
    password: str
    display_name: str = ""
    is_admin: bool = False


class ChangePasswordBody(PydanticBase):
    old_password: str
    new_password: str


class RatingBody(PydanticBase):
    rating: int


class TagsBody(PydanticBase):
    tags: list[str]


class RenameTagBody(PydanticBase):
    name: str


class BatchTagBody(PydanticBase):
    media_ids: list[int]
    tags: list[str]


class BatchTagRemoveBody(PydanticBase):
    media_ids: list[int]
    tags: list[str]


class BatchRatingBody(PydanticBase):
    media_ids: list[int]
    rating: int


class UpdateMetadataBody(PydanticBase):
    date_taken: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    location_label: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    lens_model: str | None = None
    aperture: float | None = None
    shutter_speed: str | None = None
    iso: int | None = None
    focal_length: float | None = None


def serialize_media_brief(m: Any, md: Any = None) -> dict[str, Any]:
    """Lightweight serialisation for list views (with optional metadata)."""
    result: dict[str, Any] = {
        "id": m.id,
        "filename": m.filename,
        "extension": m.extension,
        "media_type": m.media_type.value,
        "file_size": m.file_size,
        "rating": m.rating,
    }
    if md:
        result["width"] = md.width
        result["height"] = md.height
        result["date_taken"] = md.date_taken.isoformat() if md.date_taken else None
        result["camera_model"] = md.camera_model or None
        result["duration"] = md.duration
        result["gps_lat"] = md.gps_lat
        result["gps_lon"] = md.gps_lon
        result["location_label"] = md.location_label
    return result


async def serialize_media(m: Any, repo: Any) -> dict[str, Any]:
    """Convert a Media DTO + metadata/tags to JSON-safe dict."""
    md = await repo.get_metadata(m.id) if m.id else None
    tags_info = await repo.tags_for_media(m.id) if m.id else []

    result: dict[str, Any] = {
        "id": m.id,
        "path": str(m.path),  # Path object needs string conversion
        "filename": m.filename,
        "extension": m.extension,
        "media_type": m.media_type.value if hasattr(m.media_type, "value") else m.media_type,
        "file_size": m.file_size,
        "file_hash": m.file_hash,
        "rating": m.rating,
        "scanned_at": m.scanned_at.isoformat() if m.scanned_at else None,
    }

    if md:
        result["metadata"] = {
            "date_taken": md.date_taken.isoformat() if md.date_taken else None,
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
            "location_label": md.location_label,
            "location_country": md.location_country,
            "location_city": md.location_city,
        }
    else:
        result["metadata"] = None

    result["tags"] = [
        {
            "name": t.name,
            "source": t.source.value if hasattr(t.source, "value") else t.source,
            "confidence": c,
        }
        for t, c in tags_info
    ]

    return result
