"""Metadata extraction — EXIF (via exiftool) and video/audio (via ffprobe)."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from uom.config import AUDIO_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from uom.db.repository import Metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_json(cmd: list[str]) -> dict[str, Any]:
    """Run a command and return parsed JSON output (or empty dict on failure)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)  # type: ignore[no-any-return]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return {}


def _parse_exif_date(value: str | None) -> datetime | None:
    """Parse EXIF date strings like '2023:07:15 19:43:48'."""
    if not value:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
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
    tags = ff.get("tags", {})

    date_str = (
        tags.get("creation_time")
        or exif.get("EXIF:DateTimeOriginal")
        or exif.get("QuickTime:CreateDate")
    )

    return Metadata(
        media_id=media_id,
        date_taken=_parse_exif_date(date_str),
        camera_make=str(
            exif.get("EXIF:Make", "") or tags.get("com.apple.quicktime.make", "") or ""
        ),
        camera_model=str(
            exif.get("EXIF:Model", "") or tags.get("com.apple.quicktime.model", "") or ""
        ),
        lens_model=str(exif.get("EXIF:LensModel", "") or ""),
        width=_safe_int(ff.get("width") or ff.get("coded_width")),
        height=_safe_int(ff.get("height") or ff.get("coded_height")),
        duration=_safe_float(ff.get("duration")),
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
