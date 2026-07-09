"""ffprobe-backed media info extraction for organizer detail views."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from mm.server.organizer_schemas import OrganizerMediaInfo, OrganizerStreamInfo

_FFPROBE = shutil.which("ffprobe")


def organizer_media_info(path: Path) -> OrganizerMediaInfo | None:
    if not _FFPROBE or path.suffix.lower() not in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
        return None
    try:
        completed = subprocess.run(
            [
                _FFPROBE,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    streams = data.get("streams")
    if not isinstance(streams, list):
        return None
    video_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ),
        None,
    )
    fmt = data.get("format") if isinstance(data.get("format"), dict) else {}
    return OrganizerMediaInfo(
        duration=_float_or_none(fmt.get("duration") or (video_stream or {}).get("duration")),
        width=_int_or_none((video_stream or {}).get("width")),
        height=_int_or_none((video_stream or {}).get("height")),
        aspect_ratio=_aspect_ratio(video_stream),
        video_codec=str((video_stream or {}).get("codec_name") or ""),
        frame_rate=_frame_rate((video_stream or {}).get("avg_frame_rate")),
        video_bit_rate=_int_or_none((video_stream or {}).get("bit_rate") or fmt.get("bit_rate")),
        video_bit_depth=_int_or_none(
            (video_stream or {}).get("bits_per_raw_sample")
            or (video_stream or {}).get("bits_per_sample")
        ),
        hdr_format=_hdr_format(video_stream),
        audio_streams=[
            _stream_info(stream)
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ],
        subtitle_streams=[
            _stream_info(stream)
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "subtitle"
        ],
    )


def _stream_info(stream: dict[str, object]) -> OrganizerStreamInfo:
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    disposition = stream.get("disposition") if isinstance(stream.get("disposition"), dict) else {}
    channels = _int_or_none(stream.get("channels"))
    return OrganizerStreamInfo(
        source="internal",
        codec=str(stream.get("codec_name") or ""),
        channels=f"{channels}ch" if channels else str(stream.get("channel_layout") or ""),
        bit_rate=_int_or_none(stream.get("bit_rate")),
        bit_depth=_int_or_none(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample")),
        language=str(tags.get("language") or ""),
        default=bool(disposition.get("default")),
        forced=bool(disposition.get("forced")),
        title=str(tags.get("title") or ""),
        format=str(stream.get("codec_name") or ""),
    )


def _aspect_ratio(stream: dict[str, object] | None) -> str:
    if not stream:
        return ""
    display = stream.get("display_aspect_ratio")
    if display:
        return str(display)
    width = _int_or_none(stream.get("width"))
    height = _int_or_none(stream.get("height"))
    if not width or not height:
        return ""
    return f"{width / height:.2f}:1"


def _hdr_format(stream: dict[str, object] | None) -> str:
    if not stream:
        return ""
    transfer = str(stream.get("color_transfer") or "")
    primaries = str(stream.get("color_primaries") or "")
    if "smpte2084" in transfer:
        return "HDR10"
    if "arib-std-b67" in transfer:
        return "HLG"
    return primaries


def _frame_rate(value: object) -> float | None:
    if not isinstance(value, str) or "/" not in value:
        return _float_or_none(value)
    numerator, denominator = value.split("/", 1)
    num = _float_or_none(numerator)
    den = _float_or_none(denominator)
    if not num or not den:
        return None
    return round(num / den, 3)


def _int_or_none(value: object) -> int | None:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
