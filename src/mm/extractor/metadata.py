"""Metadata extraction — EXIF (via exiftool) and video/audio (via ffprobe)."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from mm.config import AUDIO_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from mm.db.dto import Metadata
from mm.utils.parsing import parse_datetime, safe_float, safe_int
from mm.utils.process import run_json_command

MetadataExtractor = Callable[[Path, int], Metadata]
MetadataMode = Literal["exiftool", "pillow"]
_METADATA_EXTRACTORS: dict[str, MetadataExtractor] = {}
_DEFAULT_METADATA_EXTRACTOR: MetadataExtractor | None = None
_EXIFTOOL_BATCH_SIZE = 200
EXIFTOOL_INSTALL_HINT = (
    "Install exiftool with `brew install exiftool`, or rerun with "
    "`--metadata-mode pillow` for basic photo metadata."
)


class MetadataToolUnavailable(RuntimeError):
    def __init__(self, tool: str, hint: str) -> None:
        super().__init__(f"{tool} is required for the selected metadata mode. {hint}")
        self.tool = tool
        self.hint = hint


def normalize_metadata_mode(mode: str) -> MetadataMode:
    if mode in ("exiftool", "pillow"):
        return mode
    raise ValueError(f"Unsupported metadata mode: {mode}")


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


_EXIFTOOL: str | None = shutil.which("exiftool")


def require_metadata_mode(mode: MetadataMode) -> None:
    if mode == "exiftool" and _EXIFTOOL is None:
        raise MetadataToolUnavailable("exiftool", EXIFTOOL_INSTALL_HINT)


def _extract_exiftool(path: Path) -> dict[str, Any]:
    """Call exiftool -j and return the first result dict."""
    return _extract_exiftool_many([path]).get(path.resolve(), {})


def _extract_exiftool_many(
    paths: Sequence[Path],
    *,
    on_progress: Callable[[int], None] | None = None,
) -> dict[Path, dict[str, Any]]:
    require_metadata_mode("exiftool")
    assert _EXIFTOOL is not None
    result: dict[Path, dict[str, Any]] = {}
    resolved = [path.resolve() for path in paths]
    for i in range(0, len(resolved), _EXIFTOOL_BATCH_SIZE):
        chunk = resolved[i : i + _EXIFTOOL_BATCH_SIZE]
        data = run_json_command([_EXIFTOOL, "-j", "-n", "-G", *[str(path) for path in chunk]])
        if not isinstance(data, list):
            if on_progress:
                on_progress(len(chunk))
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            source = item.get("SourceFile")
            if source:
                result[Path(str(source)).resolve()] = item
        if on_progress:
            on_progress(len(chunk))
    return result


def _extract_pillow_photo(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image

        with Image.open(path) as img:
            exif = img.getexif()
            exif_ifd = _pillow_ifd(exif, 34665)
            return {
                "date_taken": parse_datetime(
                    str(exif_ifd.get(36867) or exif_ifd.get(36868) or exif.get(306) or "")
                ),
                "camera_make": str(exif.get(271, "") or ""),
                "camera_model": str(exif.get(272, "") or ""),
                "lens_model": str(exif_ifd.get(42036, "") or ""),
                "focal_length": safe_float(exif_ifd.get(37386)),
                "aperture": safe_float(exif_ifd.get(33437)),
                "shutter_speed": str(exif_ifd.get(33434, "") or ""),
                "iso": safe_int(exif_ifd.get(34855) or exif_ifd.get(34867)),
                "width": img.size[0],
                "height": img.size[1],
                "orientation": safe_int(exif.get(274)),
            }
    except Exception:
        return {}


def _pillow_ifd(exif: Any, tag: int) -> dict[int, Any]:
    get_ifd = getattr(exif, "get_ifd", None)
    if not get_ifd:
        return {}
    try:
        return dict(get_ifd(tag) or {})
    except Exception:
        return {}


def _needs_pillow_photo_fallback(data: dict[str, Any]) -> bool:
    return not (
        data.get("EXIF:DateTimeOriginal")
        or data.get("EXIF:CreateDate")
        or data.get("XMP:DateCreated")
    )


def _metadata_from_photo_sources(
    media_id: int,
    exif: dict[str, Any],
    pillow: dict[str, Any],
) -> Metadata:
    return Metadata(
        media_id=media_id,
        date_taken=(
            parse_datetime(
                exif.get("EXIF:DateTimeOriginal")
                or exif.get("EXIF:CreateDate")
                or exif.get("XMP:DateCreated")
            )
            or pillow.get("date_taken")
        ),
        camera_make=str(exif.get("EXIF:Make") or pillow.get("camera_make") or ""),
        camera_model=str(exif.get("EXIF:Model") or pillow.get("camera_model") or ""),
        lens_model=str(
            exif.get("EXIF:LensModel") or exif.get("XMP:Lens") or pillow.get("lens_model") or ""
        ),
        focal_length=safe_float(exif.get("EXIF:FocalLength") or pillow.get("focal_length")),
        aperture=safe_float(exif.get("EXIF:FNumber") or pillow.get("aperture")),
        shutter_speed=str(exif.get("EXIF:ExposureTime") or pillow.get("shutter_speed") or ""),
        iso=safe_int(exif.get("EXIF:ISO") or pillow.get("iso")),
        width=safe_int(
            exif.get("EXIF:ImageWidth") or exif.get("File:ImageWidth") or pillow.get("width")
        ),
        height=safe_int(
            exif.get("EXIF:ImageHeight") or exif.get("File:ImageHeight") or pillow.get("height")
        ),
        gps_lat=safe_float(exif.get("EXIF:GPSLatitude")),
        gps_lon=safe_float(exif.get("EXIF:GPSLongitude")),
        orientation=safe_int(exif.get("EXIF:Orientation") or pillow.get("orientation")),
    )


def extract_photo_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for a photo via exiftool."""
    d = _extract_exiftool(path)
    fallback = _extract_pillow_photo(path) if _needs_pillow_photo_fallback(d) else {}
    return _metadata_from_photo_sources(media_id, d, fallback)


def extract_photo_metadata_pillow(path: Path, media_id: int) -> Metadata:
    """Extract basic photo metadata without exiftool."""
    return _metadata_from_photo_sources(media_id, {}, _extract_pillow_photo(path))


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


def _metadata_from_video_sources(path: Path, media_id: int, exif: dict[str, Any]) -> Metadata:
    ff = _extract_ffprobe(path)
    ff_tags = ff.get("tags", {})

    date_candidates = [
        ff_tags.get("creation_time"),
        ff_tags.get("date"),
        exif.get("QuickTime:CreateDate"),
        exif.get("QuickTime:CreationDate"),
        exif.get("QuickTime:MediaCreateDate"),
        exif.get("QuickTime:TrackCreateDate"),
        exif.get("H264:DateTimeOriginal"),
        exif.get("Keys:CreationDate"),
        exif.get("EXIF:DateTimeOriginal"),
        exif.get("XMP:DateCreated"),
        exif.get("UserData:DateTimeOriginal"),
    ]

    date_taken = None
    for cand in date_candidates:
        if not cand:
            continue
        dt = parse_datetime(cand)
        if dt and dt.year > 1904:
            date_taken = dt
            break

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

    if lat_val is None and lon_val is None:
        coords = exif.get("QuickTime:GPSCoordinates")
        if coords and isinstance(coords, str):
            parts = coords.replace("+", "").split()
            if len(parts) >= 2:
                lat_val = safe_float(parts[0])
                lon_val = safe_float(parts[1])

    if lat_val is not None:
        gps_lat = lat_val

    if lon_val is not None:
        gps_lon = lon_val

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


def extract_video_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for a video file via ffprobe (+ exiftool for EXIF)."""
    return _metadata_from_video_sources(path, media_id, _extract_exiftool(path))


def extract_video_metadata_basic(path: Path, media_id: int) -> Metadata:
    """Extract video metadata without exiftool."""
    return _metadata_from_video_sources(path, media_id, {})


def extract_audio_metadata(path: Path, media_id: int) -> Metadata:
    """Extract metadata for an audio file via ffprobe."""
    ff = _extract_ffprobe(path)
    tags = ff.get("tags", {})

    return Metadata(
        media_id=media_id,
        date_taken=parse_datetime(tags.get("date") or tags.get("creation_time")),
        duration=safe_float(ff.get("duration")),
    )


def check_tools() -> list[str]:
    """Return list of missing external tools."""
    missing: list[str] = []
    if _EXIFTOOL is None:
        missing.append("exiftool")
    if _FFPROBE is None:
        missing.append("ffprobe")
    return missing


def extract_metadata(
    path: Path,
    media_id: int,
    *,
    mode: MetadataMode = "exiftool",
) -> Metadata:
    """Extract metadata using the registered extractor for this file extension."""
    request = MetadataExtractionRequest(path=path, media_id=media_id)
    metadata = _extract_metadata_for_mode(request.path, request.media_id, mode, {})
    try:
        result = MetadataExtractionResult(metadata=metadata)
    except ValidationError:
        raise
    return result.metadata


def extract_metadata_many(
    paths: Sequence[Path],
    media_ids: Sequence[int] | None = None,
    *,
    mode: MetadataMode = "exiftool",
    on_progress: Callable[[int], None] | None = None,
) -> list[Metadata]:
    ids = list(media_ids) if media_ids is not None else [0] * len(paths)
    if len(paths) != len(ids):
        raise ValueError("paths and media_ids must have the same length")

    resolved_paths = [path.resolve() for path in paths]
    exif_by_path = (
        _extract_exiftool_many(resolved_paths, on_progress=on_progress)
        if mode == "exiftool"
        else {}
    )
    result: list[Metadata] = []
    for path, media_id in zip(resolved_paths, ids):
        metadata = _extract_metadata_for_mode(path, media_id, mode, exif_by_path.get(path, {}))
        result.append(MetadataExtractionResult(metadata=metadata).metadata)
        if mode != "exiftool" and on_progress:
            on_progress(1)
    return result


def _extract_metadata_for_mode(
    path: Path,
    media_id: int,
    mode: MetadataMode,
    exif: dict[str, Any],
) -> Metadata:
    ext = path.suffix.lower()
    custom = _registered_custom_extractor(path)
    if custom is not None:
        return custom(path, media_id)

    if mode == "pillow":
        if ext in PHOTO_EXTENSIONS:
            return extract_photo_metadata_pillow(path, media_id)
        if ext in VIDEO_EXTENSIONS:
            return extract_video_metadata_basic(path, media_id)
        if ext in AUDIO_EXTENSIONS:
            return extract_audio_metadata(path, media_id)
        return _custom_or_default_metadata(path, media_id, extract_photo_metadata_pillow)

    require_metadata_mode("exiftool")
    if ext in PHOTO_EXTENSIONS:
        pillow = _extract_pillow_photo(path) if _needs_pillow_photo_fallback(exif) else {}
        return _metadata_from_photo_sources(media_id, exif, pillow)
    if ext in VIDEO_EXTENSIONS:
        return _metadata_from_video_sources(path, media_id, exif)
    if ext in AUDIO_EXTENSIONS:
        return extract_audio_metadata(path, media_id)
    return _custom_or_default_metadata(path, media_id, extract_photo_metadata)


def _custom_or_default_metadata(
    path: Path,
    media_id: int,
    default: MetadataExtractor,
) -> Metadata:
    return (_registered_custom_extractor(path) or default)(path, media_id)


def _registered_custom_extractor(path: Path) -> MetadataExtractor | None:
    ext = path.suffix.lower()
    if ext in PHOTO_EXTENSIONS or ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
        return None
    extractor = _METADATA_EXTRACTORS.get(ext)
    if extractor is None or extractor is _DEFAULT_METADATA_EXTRACTOR:
        return None
    return extractor


_DEFAULT_METADATA_EXTRACTOR = extract_photo_metadata
register_metadata_extractor(PHOTO_EXTENSIONS, extract_photo_metadata)
register_metadata_extractor(VIDEO_EXTENSIONS, extract_video_metadata)
register_metadata_extractor(AUDIO_EXTENSIONS, extract_audio_metadata)
