from __future__ import annotations

import mimetypes
import json
import os
import shutil
import subprocess
import threading
import uuid
from collections.abc import Callable
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

# Cap concurrent ffmpeg frame extractions so a burst of scrubbing/thumbnail
# requests can't spawn unbounded processes and saturate the CPU.
_FFMPEG_MAX_CONCURRENCY = max(2, (os.cpu_count() or 4) // 2)
_FFMPEG_SEMAPHORE = threading.BoundedSemaphore(_FFMPEG_MAX_CONCURRENCY)

# Cache ffprobe stream results per file (keyed by identity + mtime + size) so a
# single playback session (source + subtitle + preview) doesn't re-probe.
_PROBE_CACHE_MAX = 512
_PROBE_CACHE: dict[tuple[str, int, int], list[dict[str, object]]] = {}
_PROBE_LOCK = threading.Lock()

# Deduplicate concurrent builds of the same cached artifact (preview/subtitle)
# so parallel requests wait for one ffmpeg run instead of racing.
_BUILD_LOCKS: dict[Path, threading.Lock] = {}
_BUILD_LOCKS_GUARD = threading.Lock()

# Codecs commonly decodable by browser <video>/<audio> elements. Conservative:
# HEVC/AC3/DTS work in some browsers (Safari) but not others, so anything
# outside these sets is flagged as "needs native app".
_BROWSER_VIDEO_CODECS = {"h264", "avc", "vp8", "vp9", "av1", "theora"}
_BROWSER_AUDIO_CODECS = {"aac", "mp3", "mp2", "opus", "vorbis", "flac"}


class VideoTrack(BaseModel):
    index: int
    label: str
    language: str = ""
    codec: str = ""
    default: bool = False
    forced: bool = False
    url: str | None = None


class VideoMediaInfo(BaseModel):
    video_codec: str = ""
    audio_codec: str = ""
    width: int | None = None
    height: int | None = None
    hdr: str = ""
    bit_depth: int | None = None
    frame_rate: float | None = None


class VideoPlaybackSource(BaseModel):
    mode: str  # "direct" | "unsupported"
    url: str
    mime_type: str
    audio_tracks: list[VideoTrack] = Field(default_factory=list)
    subtitle_tracks: list[VideoTrack] = Field(default_factory=list)
    selected_audio_stream: int | None = None
    preserves_video: bool = False
    playable: bool = True
    unsupported_reason: str = ""
    media_info: VideoMediaInfo | None = None


def video_playback_source(
    path: Path,
    playback_id: str,
    ffmpeg: str | None,
    audio_stream: int | None = None,
    streams: list[dict[str, object]] | None = None,
) -> VideoPlaybackSource:
    if streams is None:
        streams = probe_streams(path)
    audio_tracks = audio_track_options(streams)
    subtitle_tracks = subtitle_track_options(streams, playback_id, ffmpeg)
    selected_audio = select_audio_stream(audio_tracks, audio_stream)
    info = _video_media_info(streams, selected_audio)
    reason = _unsupported_reason(path, info)

    if reason:
        return VideoPlaybackSource(
            mode="unsupported",
            url="",
            mime_type="",
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            selected_audio_stream=selected_audio,
            preserves_video=False,
            playable=False,
            unsupported_reason=reason,
            media_info=info,
        )

    return VideoPlaybackSource(
        mode="direct",
        url=f"/api/player/video?playback_id={quote(playback_id)}",
        mime_type=mimetypes.guess_type(str(path))[0] or "video/mp4",
        audio_tracks=audio_tracks,
        subtitle_tracks=subtitle_tracks,
        selected_audio_stream=selected_audio,
        preserves_video=True,
        playable=True,
        media_info=info,
    )


def _video_media_info(streams: list[dict[str, object]], selected_audio: int | None) -> VideoMediaInfo:
    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video" and not _is_cover_art(s)),
        None,
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio" and s.get("index") == selected_audio),
        next((s for s in streams if s.get("codec_type") == "audio"), None),
    )
    video_stream = video_stream or {}
    audio_stream = audio_stream or {}

    def _to_int(value: object) -> int | None:
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return None

    frame_rate: float | None = None
    avg = str(video_stream.get("avg_frame_rate") or "")
    if "/" in avg:
        num, _, den = avg.partition("/")
        try:
            n, d = float(num), float(den)
            frame_rate = round(n / d, 3) if d else None
        except ValueError:
            frame_rate = None

    return VideoMediaInfo(
        video_codec=str(video_stream.get("codec_name") or "").lower(),
        audio_codec=str(audio_stream.get("codec_name") or "").lower(),
        width=_to_int(video_stream.get("width")),
        height=_to_int(video_stream.get("height")),
        hdr=_hdr_label(video_stream),
        bit_depth=_to_int(
            video_stream.get("bits_per_raw_sample") or video_stream.get("bits_per_sample")
        ),
        frame_rate=frame_rate,
    )


def _is_cover_art(stream: dict[str, object]) -> bool:
    disposition = stream.get("disposition")
    return isinstance(disposition, dict) and bool(disposition.get("attached_pic"))


def _hdr_label(video_stream: dict[str, object]) -> str:
    transfer = str(video_stream.get("color_transfer") or "").lower()
    if "smpte2084" in transfer:
        return "HDR10"
    if "arib-std-b67" in transfer:
        return "HLG"
    return ""


def _unsupported_reason(path: Path, info: VideoMediaInfo) -> str:
    if not can_direct_play_video(path):
        return f"{path.suffix.lstrip('.').upper()} container is not supported in browsers"
    if info.video_codec and info.video_codec not in _BROWSER_VIDEO_CODECS:
        label = info.hdr or (f"{info.bit_depth}-bit" if info.bit_depth and info.bit_depth > 8 else "")
        suffix = f" {label}" if label else ""
        return f"{info.video_codec.upper()}{suffix} video is not supported in this browser"
    if info.audio_codec and info.audio_codec not in _BROWSER_AUDIO_CODECS:
        return f"{info.audio_codec.upper()} audio is not supported in this browser"
    return ""




def preview_frame_response(
    path: Path,
    playback_id: str,
    time_value: float,
    ffmpeg: str | None,
) -> FileResponse:
    if not ffmpeg:
        raise HTTPException(422, "ffmpeg is unavailable")
    target = preview_frame_path(path, playback_id, time_value)
    _ensure_artifact(target, lambda: build_preview_frame(path, target, time_value, ffmpeg))
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
    _ensure_artifact(target, lambda: build_subtitle_cache(path, target, stream_index, ffmpeg))
    return FileResponse(
        str(target),
        media_type="text/vtt",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def _ensure_artifact(target: Path, builder: Callable[[], None]) -> None:
    """Build `target` at most once even under concurrent requests."""
    if target.exists():
        return
    with _build_lock_for(target):
        if target.exists():
            return
        builder()


def _build_lock_for(target: Path) -> threading.Lock:
    with _BUILD_LOCKS_GUARD:
        lock = _BUILD_LOCKS.get(target)
        if lock is None:
            if len(_BUILD_LOCKS) > 256:
                for key in [k for k, v in _BUILD_LOCKS.items() if not v.locked()]:
                    _BUILD_LOCKS.pop(key, None)
            lock = threading.Lock()
            _BUILD_LOCKS[target] = lock
        return lock


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
        with _FFMPEG_SEMAPHORE:
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
    cache_key = _probe_cache_key(path)
    if cache_key is not None:
        with _PROBE_LOCK:
            cached = _PROBE_CACHE.get(cache_key)
        if cached is not None:
            return cached
    streams = _probe_streams_uncached(path)
    if cache_key is not None and streams:
        with _PROBE_LOCK:
            if len(_PROBE_CACHE) >= _PROBE_CACHE_MAX:
                _PROBE_CACHE.pop(next(iter(_PROBE_CACHE)), None)
            _PROBE_CACHE[cache_key] = streams
    return streams


def _probe_cache_key(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path.expanduser().resolve()), stat.st_size, stat.st_mtime_ns)


def invalidate_probe_cache(path: Path) -> None:
    """Drop the in-memory probe entry so the next call re-runs ffprobe."""
    key = _probe_cache_key(path)
    if key is None:
        return
    with _PROBE_LOCK:
        _PROBE_CACHE.pop(key, None)


def _probe_streams_uncached(path: Path) -> list[dict[str, object]]:
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
        with _FFMPEG_SEMAPHORE:
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
