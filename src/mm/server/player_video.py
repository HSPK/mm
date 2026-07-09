from __future__ import annotations

import mimetypes
import json
import shutil
import subprocess
import uuid
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mm.config import load_cli_config

DIRECT_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".ogv"}
TEXT_SUBTITLE_CODECS = {"subrip", "ass", "ssa", "webvtt", "mov_text"}
_FFPROBE = shutil.which("ffprobe")


class VideoTrack(BaseModel):
    index: int
    label: str
    language: str = ""
    codec: str = ""
    default: bool = False
    forced: bool = False
    url: str | None = None


class VideoPlaybackSource(BaseModel):
    mode: str
    url: str
    mime_type: str
    audio_tracks: list[VideoTrack] = Field(default_factory=list)
    subtitle_tracks: list[VideoTrack] = Field(default_factory=list)
    selected_audio_stream: int | None = None
    preserves_video: bool = False


def video_playback_source(
    path: Path,
    playback_id: str,
    ffmpeg: str | None,
    audio_stream: int | None = None,
) -> VideoPlaybackSource:
    streams = probe_streams(path)
    audio_tracks = audio_track_options(streams)
    subtitle_tracks = subtitle_track_options(streams, playback_id, ffmpeg)
    selected_audio = select_audio_stream(audio_tracks, audio_stream)

    if can_direct_play_video(path) and audio_stream is None:
        return VideoPlaybackSource(
            mode="direct",
            url=f"/api/player/video?playback_id={quote(playback_id)}",
            mime_type=mimetypes.guess_type(str(path))[0] or "video/mp4",
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            selected_audio_stream=selected_audio,
            preserves_video=True,
        )
    raise HTTPException(
        422,
        "Video is not browser-playable and automatic ffmpeg processing is disabled",
    )


def preview_frame_response(
    path: Path,
    playback_id: str,
    time_value: float,
    ffmpeg: str | None,
) -> FileResponse:
    if not ffmpeg:
        raise HTTPException(422, "ffmpeg is unavailable")
    target = preview_frame_path(path, playback_id, time_value)
    if not target.exists():
        build_preview_frame(path, target, time_value, ffmpeg)
    return FileResponse(
        str(target),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def subtitle_response(
    path: Path,
    playback_id: str,
    stream_index: int,
    ffmpeg: str | None,
) -> FileResponse:
    if not ffmpeg:
        raise HTTPException(422, "ffmpeg is unavailable")
    streams = probe_streams(path)
    track = next((track for track in subtitle_track_options(streams, playback_id, ffmpeg) if track.index == stream_index), None)
    if track is None or track.url is None:
        raise HTTPException(404, "Subtitle track is not available")
    target = subtitle_cache_path(path, stream_index)
    if not target.exists():
        build_subtitle_cache(path, target, stream_index, ffmpeg)
    return FileResponse(
        str(target),
        media_type="text/vtt",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def can_direct_play_video(path: Path) -> bool:
    return path.suffix.lower() in DIRECT_VIDEO_EXTENSIONS


def preview_frame_path(path: Path, playback_id: str, time_value: float) -> Path:
    stat = path.stat()
    bucket = max(0, int(time_value // 10 * 10))
    key = sha256(
        f"{path.expanduser().resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{playback_id}:{bucket}".encode()
    ).hexdigest()
    return load_cli_config().paths.cache_dir / "player-video-preview" / f"{key}.jpg"


def subtitle_cache_path(path: Path, stream_index: int) -> Path:
    stat = path.stat()
    key = sha256(
        f"{path.expanduser().resolve()}:{stat.st_size}:{stat.st_mtime_ns}:subtitle-v1:{stream_index}".encode()
    ).hexdigest()
    return load_cli_config().paths.cache_dir / "player-video-subtitles" / f"{key}.vtt"


def build_subtitle_cache(source: Path, target: Path, stream_index: int, ffmpeg: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp.vtt")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-map",
                f"0:{stream_index}",
                "-c:s",
                "webvtt",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        tmp.replace(target)
    except subprocess.CalledProcessError as exc:
        tmp.unlink(missing_ok=True)
        detail = exc.stderr.strip() or "Subtitle conversion failed"
        raise HTTPException(500, detail)


def probe_streams(path: Path) -> list[dict[str, object]]:
    if not _FFPROBE:
        return []
    try:
        completed = subprocess.run(
            [
                _FFPROBE,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []
    streams = data.get("streams")
    return [stream for stream in streams if isinstance(stream, dict)] if isinstance(streams, list) else []


def audio_track_options(streams: list[dict[str, object]]) -> list[VideoTrack]:
    return [
        stream_track(stream, "Audio")
        for stream in streams
        if stream.get("codec_type") == "audio" and isinstance(stream.get("index"), int)
    ]


def subtitle_track_options(
    streams: list[dict[str, object]],
    playback_id: str,
    ffmpeg: str | None,
) -> list[VideoTrack]:
    tracks: list[VideoTrack] = []
    for stream in streams:
        if stream.get("codec_type") != "subtitle" or not isinstance(stream.get("index"), int):
            continue
        codec = str(stream.get("codec_name") or "")
        track = stream_track(stream, "Subtitle")
        if ffmpeg and codec in TEXT_SUBTITLE_CODECS:
            track.url = (
                f"/api/player/video/subtitle?playback_id={quote(playback_id)}"
                f"&stream_index={track.index}"
            )
        tracks.append(track)
    return tracks


def stream_track(stream: dict[str, object], fallback: str) -> VideoTrack:
    index = int(stream["index"])
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    disposition = stream.get("disposition") if isinstance(stream.get("disposition"), dict) else {}
    language = str(tags.get("language") or "")
    title = str(tags.get("title") or "")
    codec = str(stream.get("codec_name") or "")
    pieces = [title, language.upper() if language else "", codec.upper() if codec else ""]
    label = " · ".join(piece for piece in pieces if piece) or f"{fallback} {index + 1}"
    return VideoTrack(
        index=index,
        label=label,
        language=language,
        codec=codec,
        default=bool(disposition.get("default")),
        forced=bool(disposition.get("forced")),
    )


def select_audio_stream(audio_tracks: list[VideoTrack], requested: int | None) -> int | None:
    if requested is not None and any(track.index == requested for track in audio_tracks):
        return requested
    default = next((track.index for track in audio_tracks if track.default), None)
    if default is not None:
        return default
    return audio_tracks[0].index if audio_tracks else None


def build_preview_frame(source: Path, target: Path, time_value: float, ffmpeg: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp.jpg")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-ss",
                str(max(0, time_value)),
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                "scale=240:-1",
                "-q:v",
                "4",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        tmp.replace(target)
    except subprocess.CalledProcessError as exc:
        tmp.unlink(missing_ok=True)
        detail = exc.stderr.strip() or "Preview frame failed"
        raise HTTPException(500, detail) from exc
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(500, "Preview frame failed") from exc
