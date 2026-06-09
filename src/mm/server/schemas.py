from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBase, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


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


class BatchDeleteBody(PydanticBase):
    media_ids: list[int]


class BatchMetadataBody(PydanticBase):
    """Bulk-apply the same metadata patch to many media."""

    media_ids: list[int]
    date_taken: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    location_label: str | None = None
    location_city: str | None = None
    location_country: str | None = None


class CreateAlbumBody(PydanticBase):
    name: str
    description: str = ""


class AlbumMediaBody(PydanticBase):
    media_ids: list[int]


class SmartAlbumBody(PydanticBase):
    """Create or update a smart album definition."""

    key: str
    section: str = "custom"
    title: str
    subtitle: str = ""
    icon: str = "images"
    color: str = ""
    filters: dict = {}
    generator: str | None = None
    generator_config: dict = {}
    position: int = 0
    enabled: bool = True


class SmartAlbumUpdateBody(PydanticBase):
    """Partial update for an existing smart album definition."""

    key: str | None = None
    section: str | None = None
    title: str | None = None
    subtitle: str | None = None
    icon: str | None = None
    color: str | None = None
    filters: dict | None = None
    generator: str | None = None
    generator_config: dict | None = None
    position: int | None = None
    enabled: bool | None = None


class SwitchLibraryBody(PydanticBase):
    """Request body for switching the active library database."""

    db_path: str


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


# ---------------------------------------------------------------------------
# Response models — appear in openapi.json so clients can type their decoders
# ---------------------------------------------------------------------------


class MediaBrief(PydanticBase):
    """Lightweight media row used in list views (grid pagination)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    filename: str
    extension: str
    media_type: str
    file_size: int
    rating: int
    width: int | None = None
    height: int | None = None
    date_taken: str | None = None
    camera_model: str | None = None
    duration: float | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    location_label: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    deleted_at: str | None = None


class MediaMetadata(PydanticBase):
    """Full per-item EXIF/derived metadata payload."""

    date_taken: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    lens_model: str | None = None
    focal_length: float | None = None
    aperture: float | None = None
    shutter_speed: str | None = None
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


class MediaTag(PydanticBase):
    name: str
    source: str
    confidence: float | None = None


class MediaDetail(PydanticBase):
    """Full media detail with metadata + tags (used by viewer/info panel)."""

    id: int
    path: str
    filename: str
    extension: str
    media_type: str
    file_size: int
    file_hash: str
    rating: int
    scanned_at: str | None = None
    metadata: MediaMetadata | None = None
    tags: list[MediaTag] = []


class PaginatedMedia(PydanticBase):
    items: list[MediaBrief]
    total: int
    page: int
    per_page: int
    pages: int


class RatingResponse(PydanticBase):
    rating: int


class BatchAffected(PydanticBase):
    """Server reports how many items were actually mutated by a batch op."""

    affected: int


class UserSummary(PydanticBase):
    id: int
    username: str
    display_name: str
    is_admin: bool


class UserDetail(UserSummary):
    """List view payload returned by `GET /api/users`."""

    created_at: str | None = None


class LoginResponse(PydanticBase):
    token: str
    user: UserSummary


class AuthStatus(PydanticBase):
    setup_required: bool


class AlbumSummary(PydanticBase):
    """Summary returned by GET /api/albums."""

    id: int
    name: str
    description: str | None = None
    cover_media_id: int | None = None
    count: int = 0
    created_at: str | None = None


class CreatedAlbum(PydanticBase):
    """Mirrors what AlbumsApi.create returns — same shape as AlbumSummary."""

    id: int
    name: str
    description: str | None = None
    cover_media_id: int | None = None
    count: int = 0
    created_at: str | None = None


class AlbumActionResponse(PydanticBase):
    """Acknowledgement for add/remove-media album mutations."""

    message: str
    affected: int


class CameraStats(PydanticBase):
    make: str
    model: str
    count: int


class TagStats(PydanticBase):
    id: int
    name: str
    count: int


class TimelineEntry(PydanticBase):
    """One bucket in the timeline distribution (year-month or year)."""

    model_config = ConfigDict(extra="allow")

    period: str
    count: int


class TypeDistribution(PydanticBase):
    photo: int = 0
    video: int = 0
    audio: int = 0


class LibraryStats(PydanticBase):
    total_files: int
    total_size: int
    type_distribution: TypeDistribution
    tags: list[TagStats]
    cameras: list[CameraStats]


class LibraryInfo(PydanticBase):
    db_path: str
    name: str
    library_id: str | None = None


class SwitchLibraryResponse(PydanticBase):
    db_path: str
    name: str
    message: str


class SmartAlbumEntry(PydanticBase):
    """One smart-album manifest as exposed by /api/smart-albums."""

    model_config = ConfigDict(extra="ignore")

    key: str
    title: str
    subtitle: str = ""
    count: int | None = None
    cover_id: int | None = None
    icon: str | None = None
    color: str = ""
    filters: dict = Field(default_factory=dict)
    search_text: str | None = None
    festival_id: str | None = None


class SmartAlbumsResponse(PydanticBase):
    library: list[SmartAlbumEntry] = []
    tags: list[SmartAlbumEntry] = []
    cameras: list[SmartAlbumEntry] = []
    festivals: list[SmartAlbumEntry] = []
    years: list[SmartAlbumEntry] = []
    places: list[SmartAlbumEntry] = []


class SmartAlbumDefinition(PydanticBase):
    """Raw smart-album definition row used by admin CRUD endpoints."""

    model_config = ConfigDict(extra="allow")

    id: int
    key: str
    section: str = "custom"
    title: str
    subtitle: str = ""
    icon: str = "images"
    color: str = ""
    filters: dict = Field(default_factory=dict)
    generator: str | None = None
    generator_config: dict = Field(default_factory=dict)
    position: int = 0
    enabled: bool = True
    is_system: int = 0


class SmartAlbumResetResult(PydanticBase):
    status: str = "ok"
    seeded: int


class DuplicateGroup(PydanticBase):
    """Cluster of media that share the same file_hash."""

    file_hash: str
    count: int
    items: list[MediaBrief]


class GeoPoint(PydanticBase):
    """Compact map marker payload — `/api/geo` returns this in bulk."""

    id: int
    filename: str
    media_type: str
    lat: float
    lon: float
    date: str | None = None
    city: str | None = None


class StatusMessage(PydanticBase):
    """Generic acknowledgement payload."""

    message: str


class StatusOk(PydanticBase):
    """Acknowledgement payload using `status: "ok"` shape."""

    status: str = "ok"


# ---------------------------------------------------------------------------
# Serializers — return Pydantic instances; FastAPI emits the same JSON shape
# ---------------------------------------------------------------------------


def serialize_media_brief(m: Any, md: Any = None) -> MediaBrief:
    """Lightweight serialisation for list views (with optional metadata)."""
    deleted_at: str | None = None
    if m.deleted_at:
        deleted_at = m.deleted_at.isoformat() if hasattr(m.deleted_at, "isoformat") else str(m.deleted_at)

    payload: dict[str, Any] = {
        "id": m.id,
        "filename": m.filename,
        "extension": m.extension,
        "media_type": m.media_type.value,
        "file_size": m.file_size,
        "rating": m.rating,
        "deleted_at": deleted_at,
    }
    if md:
        payload.update(
            width=md.width,
            height=md.height,
            date_taken=md.date_taken.isoformat() if md.date_taken else None,
            camera_model=md.camera_model or None,
            duration=md.duration,
            gps_lat=md.gps_lat,
            gps_lon=md.gps_lon,
            location_label=md.location_label,
            location_city=md.location_city,
            location_country=md.location_country,
        )
    return MediaBrief.model_validate(payload)


async def serialize_media(m: Any, db: Any) -> MediaDetail:
    """Convert a Media DTO + metadata/tags to a MediaDetail."""
    md = await db.metadata.get(m.id) if m.id else None
    tags_info = await db.tag.for_media(m.id) if m.id else []

    metadata: MediaMetadata | None = None
    if md:
        metadata = MediaMetadata(
            date_taken=md.date_taken.isoformat() if md.date_taken else None,
            camera_make=md.camera_make,
            camera_model=md.camera_model,
            lens_model=md.lens_model,
            focal_length=md.focal_length,
            aperture=md.aperture,
            shutter_speed=md.shutter_speed,
            iso=md.iso,
            width=md.width,
            height=md.height,
            duration=md.duration,
            gps_lat=md.gps_lat,
            gps_lon=md.gps_lon,
            orientation=md.orientation,
            location_label=md.location_label,
            location_country=md.location_country,
            location_city=md.location_city,
        )

    tags = [
        MediaTag(
            name=t.name,
            source=t.source.value if hasattr(t.source, "value") else t.source,
            confidence=c,
        )
        for t, c in tags_info
    ]

    return MediaDetail(
        id=m.id,
        path=str(m.path),
        filename=m.filename,
        extension=m.extension,
        media_type=m.media_type.value if hasattr(m.media_type, "value") else m.media_type,
        file_size=m.file_size,
        file_hash=m.file_hash,
        rating=m.rating,
        scanned_at=m.scanned_at.isoformat() if m.scanned_at else None,
        metadata=metadata,
        tags=tags,
    )
