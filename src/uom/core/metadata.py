"""Metadata extraction — EXIF (via exiftool) and video/audio (via ffprobe)."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from uom.config import AUDIO_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from uom.db.dto import Metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_json(cmd: list[str]) -> dict[str, Any]:
    """Run a command and return parsed JSON output (or empty dict on failure)."""
    try:
        # Use errors='replace' to avoid UnicodeDecodeError on weird metadata
        result = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=30
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)  # type: ignore[no-any-return]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, UnicodeError):
        return {}


def _parse_exif_date(value: str | None) -> datetime | None:
    """Parse EXIF date strings like '2023:07:15 19:43:48'."""
    if not value:
        return None
    # Try ISO format first (handles Z, T, etc.)
    try:
        # standard ISO parsing (Python 3.7+)
        # Handles 2010-01-01T12:00:00.000000Z
        dt_obj = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Naive datetime is usually preferred in this app context, so remove tzinfo
        # to avoid mismatch with DB native datetimes (which are naive).
        return dt_obj.replace(tzinfo=None)
    except ValueError:
        pass

    # Common formats
    formats = (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",  # 2024-01-01 12:00:00.000
    )
    for fmt in formats:
        try:
            # Handle potential trailing timezone or fractional seconds crudely if needed
            # But strip() helps
            # Also handle potentially localized strings if simple
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

    return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# exiftool-based extraction
# ---------------------------------------------------------------------------

_EXIFTOOL: str | None = shutil.which("exiftool")


def _extract_exiftool(path: Path) -> dict[str, Any]:
    """Call exiftool -j and return the first result dict."""
    if _EXIFTOOL is None:
        return {}
    data = _run_json([_EXIFTOOL, "-j", "-n", "-G", str(path)])
    if isinstance(data, list) and data:
        return data[0]
    return {}


def extract_photo_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for a photo via exiftool."""
    d = _extract_exiftool(path)
    return Metadata(
        media_id=media_id,
        date_taken=_parse_exif_date(
            d.get("EXIF:DateTimeOriginal") or d.get("EXIF:CreateDate") or d.get("XMP:DateCreated")
        ),
        camera_make=str(d.get("EXIF:Make", "") or ""),
        camera_model=str(d.get("EXIF:Model", "") or ""),
        lens_model=str(d.get("EXIF:LensModel", "") or d.get("XMP:Lens", "") or ""),
        focal_length=_safe_float(d.get("EXIF:FocalLength")),
        aperture=_safe_float(d.get("EXIF:FNumber")),
        shutter_speed=str(d.get("EXIF:ExposureTime", "") or ""),
        iso=_safe_int(d.get("EXIF:ISO")),
        width=_safe_int(d.get("EXIF:ImageWidth") or d.get("File:ImageWidth")),
        height=_safe_int(d.get("EXIF:ImageHeight") or d.get("File:ImageHeight")),
        gps_lat=_safe_float(d.get("EXIF:GPSLatitude")),
        gps_lon=_safe_float(d.get("EXIF:GPSLongitude")),
        orientation=_safe_int(d.get("EXIF:Orientation")),
    )


# ---------------------------------------------------------------------------
# ffprobe-based extraction
# ---------------------------------------------------------------------------

_FFPROBE: str | None = shutil.which("ffprobe")


def _extract_ffprobe(path: Path) -> dict[str, Any]:
    """Call ffprobe and return combined format + first stream info."""
    if _FFPROBE is None:
        return {}
    data = _run_json(
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
        # Filter out obvious bad dates if needed, but _parse_exif_date just parses.
        # We'll parse first.
        dt = _parse_exif_date(cand)
        if dt and dt.year > 1904:  # 1904 is mp4 epoch start, often default value
            date_taken = dt
            break

    # Try to extract GPS from QuickTime/Keys tags
    gps_lat: float | None = None
    gps_lon: float | None = None

    # Check common GPS keys in exiftool output
    lat_ref = str(
        exif.get("Composite:GPSLatitudeRef", "") or exif.get("EXIF:GPSLatitudeRef", "")
    ).upper()
    lon_ref = str(
        exif.get("Composite:GPSLongitudeRef", "") or exif.get("EXIF:GPSLongitudeRef", "")
    ).upper()

    lat_val = _safe_float(
        exif.get("Composite:GPSLatitude")
        or exif.get("EXIF:GPSLatitude")
        or exif.get("QuickTime:GPSCoordinates-lat")
        or exif.get("Keys:GPSCoordinates-lat")
    )
    lon_val = _safe_float(
        exif.get("Composite:GPSLongitude")
        or exif.get("EXIF:GPSLongitude")
        or exif.get("QuickTime:GPSCoordinates-lon")
        or exif.get("Keys:GPSCoordinates-lon")
    )

    # Some tools return signed float directly (e.g. QuickTime:GPSCoordinates is often a string like "30.123 120.456")
    # But usually exiftool -n -j gives decimal degrees.
    # If not using -n (which we use), we might get "30 deg 12' 34""
    # But we use -n in _extract_exiftool, so values should be decimal.

    # QuickTime:GPSCoordinates sometimes is "lat, lon, alt" string
    if lat_val is None and lon_val is None:
        coords = exif.get("QuickTime:GPSCoordinates")
        if coords and isinstance(coords, str):
            parts = coords.replace("+", "").split()  # "30.1234 120.5678"
            if len(parts) >= 2:
                lat_val = _safe_float(parts[0])
                lon_val = _safe_float(parts[1])

    if lat_val is not None:
        gps_lat = lat_val
        # Adjust for Ref if value is positive but Ref is South (rare with -n?)
        # With -n, exiftool usually returns signed value for Composite tags.
        # But for EXIF tags it might follow Ref.
        # Let's trust the value if it's signed (handled by exiftool -n).

    if lon_val is not None:
        gps_lon = lon_val

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
        width=_safe_int(ff.get("width") or ff.get("coded_width")),
        height=_safe_int(ff.get("height") or ff.get("coded_height")),
        duration=_safe_float(ff.get("duration")),
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )


def extract_audio_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for an audio file via ffprobe."""
    ff = _extract_ffprobe(path)
    tags = ff.get("tags", {})

    return Metadata(
        media_id=media_id,
        date_taken=_parse_exif_date(tags.get("date") or tags.get("creation_time")),
        duration=_safe_float(ff.get("duration")),
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


# ---------------------------------------------------------------------------
# Unified dispatcher
# ---------------------------------------------------------------------------


def extract_metadata(path: Path, media_id: int) -> Metadata:
    """Auto-dispatch to the correct extractor based on file extension."""
    ext = path.suffix.lower()
    if ext in PHOTO_EXTENSIONS:
        return extract_photo_metadata(path, media_id)
    if ext in VIDEO_EXTENSIONS:
        return extract_video_metadata(path, media_id)
    if ext in AUDIO_EXTENSIONS:
        return extract_audio_metadata(path, media_id)
    # Fallback: try exiftool
    return extract_photo_metadata(path, media_id)
