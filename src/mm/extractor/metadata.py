"""Metadata extraction — EXIF (via exiftool) and video/audio (via ffprobe)."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from mm.config import AUDIO_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from mm.db.dto import Metadata
from mm.utils.parsing import parse_datetime, safe_float, safe_int
from mm.utils.process import run_json_command

MetadataExtractor = Callable[[Path, int], Metadata]
_METADATA_EXTRACTORS: dict[str, MetadataExtractor] = {}
_DEFAULT_METADATA_EXTRACTOR: MetadataExtractor | None = None


class MetadataExtractorRegistration(BaseModel):
    """A strictly validated metadata extractor registration."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, strict=True)

    extensions: tuple[str, ...] = Field(min_length=1)
    extractor: MetadataExtractor

    @field_validator("extensions")
    @classmethod
    def normalize_extensions(cls, extensions: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for ext in extensions:
            value = ext.lower()
            normalized.append(value if value.startswith(".") else f".{value}")
        return tuple(normalized)


class MetadataExtractionRequest(BaseModel):
    """Strictly validated extractor input."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, strict=True)

    path: Path
    media_id: int


class MetadataExtractionResult(BaseModel):
    """Strictly validated extractor output."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, strict=True)

    metadata: Metadata

    @field_validator("metadata", mode="before")
    @classmethod
    def require_metadata(cls, metadata: object) -> Metadata:
        if not isinstance(metadata, Metadata):
            raise ValueError("metadata extractor must return mm.db.dto.Metadata")
        return metadata


def register_metadata_extractor(
    extensions: Iterable[str],
    extractor: MetadataExtractor,
) -> None:
    """Register one extractor for one or more file extensions."""
    registration = MetadataExtractorRegistration(
        extensions=tuple(extensions),
        extractor=extractor,
    )
    for ext in registration.extensions:
        _METADATA_EXTRACTORS[ext] = registration.extractor


def get_metadata_extractor(path: Path) -> MetadataExtractor:
    """Return the registered extractor for *path*, falling back to the default."""
    request = MetadataExtractionRequest(path=path, media_id=0)
    extractor = _METADATA_EXTRACTORS.get(request.path.suffix.lower())
    if extractor is not None:
        return extractor
    if _DEFAULT_METADATA_EXTRACTOR is None:
        raise RuntimeError("No default metadata extractor registered")
    return _DEFAULT_METADATA_EXTRACTOR

# ---------------------------------------------------------------------------
# exiftool-based extraction
# ---------------------------------------------------------------------------

_EXIFTOOL: str | None = shutil.which("exiftool")


def _extract_exiftool(path: Path) -> dict[str, Any]:
    """Call exiftool -j and return the first result dict."""
    if _EXIFTOOL is None:
        return {}
    data = run_json_command([_EXIFTOOL, "-j", "-n", "-G", str(path)])
    if isinstance(data, list) and data:
        return data[0]
    return {}


def extract_photo_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for a photo via exiftool."""
    d = _extract_exiftool(path)
    return Metadata(
        media_id=media_id,
        date_taken=parse_datetime(
            d.get("EXIF:DateTimeOriginal")
            or d.get("EXIF:CreateDate")
            or d.get("XMP:DateCreated")
        ),
        camera_make=str(d.get("EXIF:Make", "") or ""),
        camera_model=str(d.get("EXIF:Model", "") or ""),
        lens_model=str(d.get("EXIF:LensModel", "") or d.get("XMP:Lens", "") or ""),
        focal_length=safe_float(d.get("EXIF:FocalLength")),
        aperture=safe_float(d.get("EXIF:FNumber")),
        shutter_speed=str(d.get("EXIF:ExposureTime", "") or ""),
        iso=safe_int(d.get("EXIF:ISO")),
        width=safe_int(d.get("EXIF:ImageWidth") or d.get("File:ImageWidth")),
        height=safe_int(d.get("EXIF:ImageHeight") or d.get("File:ImageHeight")),
        gps_lat=safe_float(d.get("EXIF:GPSLatitude")),
        gps_lon=safe_float(d.get("EXIF:GPSLongitude")),
        orientation=safe_int(d.get("EXIF:Orientation")),
    )


# ---------------------------------------------------------------------------
# ffprobe-based extraction
# ---------------------------------------------------------------------------

_FFPROBE: str | None = shutil.which("ffprobe")


def _extract_ffprobe(path: Path) -> dict[str, Any]:
    """Call ffprobe and return combined format + first stream info."""
    if _FFPROBE is None:
        return {}
    data = run_json_command(
        [
            _FFPROBE,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    result: dict[str, Any] = {}
    fmt = data.get("format", {})
    result.update(fmt)
    result["tags"] = {**(fmt.get("tags") or {})}
    streams = data.get("streams", [])
    for s in streams:
        if s.get("codec_type") in ("video", "audio"):
            result.update(s)
            result["tags"].update(s.get("tags") or {})
            break
    return result


def extract_video_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for a video file via ffprobe (+ exiftool for EXIF)."""
    ff = _extract_ffprobe(path)
    exif = _extract_exiftool(path)
    ff_tags = ff.get("tags", {})

    # ffprobe 'tags' is often from format. Also check first video/audio stream tags.
    # _extract_ffprobe already merges stream tags into 'tags', so we are good there.
    # But let's check explicit keys in prioritized order.

    date_candidates = [
        ff_tags.get("creation_time"),  # Standard QuickTime/MP4 creation time
        ff_tags.get("date"),  # Sometimes just 'date'
        exif.get("QuickTime:CreateDate"),
        exif.get("QuickTime:CreationDate"),
        exif.get("QuickTime:MediaCreateDate"),
        exif.get("QuickTime:TrackCreateDate"),
        exif.get("H264:DateTimeOriginal"),
        exif.get("Keys:CreationDate"),
        exif.get("EXIF:DateTimeOriginal"),
        exif.get("XMP:DateCreated"),
        exif.get("UserData:DateTimeOriginal"),  # Some cameras put it here
    ]

    date_taken = None
    for cand in date_candidates:
        if not cand:
            continue
        # Sometimes creation_time is 1904-01-01 (epoch for MP4) which is invalid/default
        # Filter out obvious bad dates after parsing.
        # We'll parse first.
        dt = parse_datetime(cand)
        if dt and dt.year > 1904:  # 1904 is mp4 epoch start, often default value
            date_taken = dt
            break

    # Try to extract GPS from QuickTime/Keys tags
    gps_lat: float | None = None
    gps_lon: float | None = None

    lat_val = safe_float(
        exif.get("Composite:GPSLatitude")
        or exif.get("EXIF:GPSLatitude")
        or exif.get("QuickTime:GPSCoordinates-lat")
        or exif.get("Keys:GPSCoordinates-lat")
    )
    lon_val = safe_float(
        exif.get("Composite:GPSLongitude")
        or exif.get("EXIF:GPSLongitude")
        or exif.get("QuickTime:GPSCoordinates-lon")
        or exif.get("Keys:GPSCoordinates-lon")
    )

    # Some tools return signed float directly (e.g. "30.123 120.456").
    # But usually exiftool -n -j gives decimal degrees.
    # If not using -n (which we use), we might get "30 deg 12' 34""
    # But we use -n in _extract_exiftool, so values should be decimal.

    # QuickTime:GPSCoordinates sometimes is "lat, lon, alt" string
    if lat_val is None and lon_val is None:
        coords = exif.get("QuickTime:GPSCoordinates")
        if coords and isinstance(coords, str):
            parts = coords.replace("+", "").split()  # "30.1234 120.5678"
            if len(parts) >= 2:
                lat_val = safe_float(parts[0])
                lon_val = safe_float(parts[1])

    if lat_val is not None:
        gps_lat = lat_val

    if lon_val is not None:
        gps_lon = lon_val

    # (0, 0) is the Gulf of Guinea — treat as "no GPS data"
    if gps_lat == 0.0 and gps_lon == 0.0:
        gps_lat = None
        gps_lon = None

    return Metadata(
        media_id=media_id,
        date_taken=date_taken,
        camera_make=str(
            exif.get("EXIF:Make", "")
            or ff_tags.get("com.apple.quicktime.make", "")
            or exif.get("QuickTime:Make", "")
            or ""
        ),
        camera_model=str(
            exif.get("EXIF:Model", "")
            or ff_tags.get("com.apple.quicktime.model", "")
            or exif.get("QuickTime:Model", "")
            or ""
        ),
        lens_model=str(exif.get("EXIF:LensModel", "") or ""),
        width=safe_int(ff.get("width") or ff.get("coded_width")),
        height=safe_int(ff.get("height") or ff.get("coded_height")),
        duration=safe_float(ff.get("duration")),
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )


def extract_audio_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for an audio file via ffprobe."""
    ff = _extract_ffprobe(path)
    tags = ff.get("tags", {})

    return Metadata(
        media_id=media_id,
        date_taken=parse_datetime(tags.get("date") or tags.get("creation_time")),
        duration=safe_float(ff.get("duration")),
    )


# ---------------------------------------------------------------------------
# Tool availability check
# ---------------------------------------------------------------------------


def check_tools() -> list[str]:
    """Return list of missing external tools."""
    missing: list[str] = []
    if _EXIFTOOL is None:
        missing.append("exiftool")
    if _FFPROBE is None:
        missing.append("ffprobe")
    return missing


def extract_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata using the registered extractor for this file extension."""
    request = MetadataExtractionRequest(path=path, media_id=media_id)
    extractor = get_metadata_extractor(request.path)
    try:
        result = MetadataExtractionResult(
            metadata=extractor(request.path, request.media_id),
        )
    except ValidationError:
        raise
    return result.metadata


_DEFAULT_METADATA_EXTRACTOR = extract_photo_metadata
register_metadata_extractor(PHOTO_EXTENSIONS, extract_photo_metadata)
register_metadata_extractor(VIDEO_EXTENSIONS, extract_video_metadata)
register_metadata_extractor(AUDIO_EXTENSIONS, extract_audio_metadata)
