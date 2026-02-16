"""Peewee ORM models for UOM's SQLite database."""

from __future__ import annotations

import datetime as dt
from enum import Enum

from peewee import (
    AutoField,
    BlobField,
    CharField,
    CompositeKey,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SmallIntegerField,
    SqliteDatabase,
    TextField,
)

# ---------------------------------------------------------------------------
# Enums (kept for use throughout the project)
# ---------------------------------------------------------------------------


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"


class TagSource(str, Enum):
    MANUAL = "manual"
    RULE = "rule"
    AUTO_CLIP = "auto-clip"


# ---------------------------------------------------------------------------
# Database proxy — bound at runtime by Repository
# ---------------------------------------------------------------------------

# Use standard SqliteDatabase.
database = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = database

    class Meta:
        database = database


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class MediaModel(BaseModel):
    id = AutoField()
    path = TextField(unique=True)
    filename = TextField()
    extension = CharField(max_length=16)
    media_type = CharField(max_length=16)
    file_size = IntegerField(default=0)
    file_hash = CharField(max_length=64, default="")
    rating = SmallIntegerField(default=0)  # 0-5 stars
    created_at = DateTimeField(null=True)
    modified_at = DateTimeField(null=True)
    scanned_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        table_name = "media"
        indexes = (
            (("file_hash",), False),
            (("media_type",), False),
            (("rating",), False),
        )


class MetadataModel(BaseModel):
    id = AutoField()
    media = ForeignKeyField(MediaModel, backref="metadata_set", unique=True, on_delete="CASCADE")
    date_taken = DateTimeField(null=True)
    camera_make = CharField(max_length=128, default="")
    camera_model = CharField(max_length=128, default="")
    lens_model = CharField(max_length=128, default="")
    focal_length = FloatField(null=True)
    aperture = FloatField(null=True)
    shutter_speed = CharField(max_length=32, default="")
    iso = IntegerField(null=True)
    width = IntegerField(null=True)
    height = IntegerField(null=True)
    duration = FloatField(null=True)
    gps_lat = FloatField(null=True)
    gps_lon = FloatField(null=True)
    orientation = IntegerField(null=True)
    location_label = CharField(max_length=256, null=True, default=None)
    location_country = CharField(max_length=64, null=True, default=None)
    location_city = CharField(max_length=64, null=True, default=None)

    class Meta:
        table_name = "metadata"
        indexes = ((("date_taken",), False),)


class TagModel(BaseModel):
    id = AutoField()
    name = CharField(max_length=128, unique=True)
    source = CharField(max_length=16, default=TagSource.MANUAL.value)
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        table_name = "tags"


class MediaTagModel(BaseModel):
    media = ForeignKeyField(MediaModel, backref="media_tags", on_delete="CASCADE")
    tag = ForeignKeyField(TagModel, backref="media_tags", on_delete="CASCADE")
    confidence = FloatField(default=1.0)
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        table_name = "media_tags"
        primary_key = CompositeKey("media", "tag")


class EmbeddingModel(BaseModel):
    id = AutoField()
    media = ForeignKeyField(MediaModel, backref="embeddings", unique=True, on_delete="CASCADE")
    vector = BlobField()
    model = CharField(max_length=64, default="")
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        table_name = "embeddings"


class UserModel(BaseModel):
    id = AutoField()
    username = CharField(max_length=64, unique=True)
    password_hash = CharField(max_length=256)
    display_name = CharField(max_length=128, default="")
    is_admin = SmallIntegerField(default=0)
    token = CharField(max_length=128, null=True, index=True)
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        table_name = "users"


ALL_TABLES = [MediaModel, MetadataModel, TagModel, MediaTagModel, EmbeddingModel, UserModel]
