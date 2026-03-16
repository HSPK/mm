"""Lightweight dataclasses used as DTOs across the codebase.

Kept thin so callers don't need to import Peewee model classes directly.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from mm.db.models import MediaType, TagSource


@dataclass
class Media:
    id: int | None = None
    path: str = ""
    filename: str = ""
    extension: str = ""
    media_type: MediaType = MediaType.PHOTO
    file_size: int = 0
    file_hash: str = ""
    rating: int = 0
    created_at: dt.datetime | None = None
    modified_at: dt.datetime | None = None
    scanned_at: dt.datetime | None = None
    deleted_at: dt.datetime | None = None


@dataclass
class Metadata:
    id: int | None = None
    media_id: int = 0
    date_taken: dt.datetime | None = None
    camera_make: str = ""
    camera_model: str = ""
    lens_model: str = ""
    focal_length: float | None = None
    aperture: float | None = None
    shutter_speed: str = ""
    iso: int | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    orientation: int | None = None
    location_label: str | None = None
    location_country: str | None = None
    location_city: str | None = None


@dataclass
class Tag:
    id: int | None = None
    name: str = ""
    source: TagSource = TagSource.MANUAL
    created_at: dt.datetime | None = None


@dataclass
class Embedding:
    id: int | None = None
    media_id: int = 0
    vector: bytes = b""
    model: str = ""
    created_at: dt.datetime | None = None


@dataclass
class User:
    id: int | None = None
    username: str = ""
    display_name: str = ""
    is_admin: bool = False
    created_at: dt.datetime | None = None
