from __future__ import annotations

import mimetypes
import json
import re
import shutil
import subprocess
import time
import uuid
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mm.config import load_cli_config
from mm.io import local_storage
from mm.server.utils import stream_file

HLS_SEGMENT_RE = re.compile(r"^seg_\d{5}\.ts$")
DIRECT_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".ogv"}
REMUX_VIDEO_CODECS = {"h264", "hevc", "h265", "av1"}
TEXT_SUBTITLE_CODECS = {"subrip", "ass", "ssa", "webvtt", "mov_text"}
HLS_PROCESSES: dict[str, subprocess.Popen] = {}
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
    if ffmpeg and can_remux_video_stream(streams):
        params = f"playback_id={quote(playback_id)}"
        if selected_audio is not None:
            params += f"&audio_stream={selected_audio}"
        return VideoPlaybackSource(
            mode="remux",
            url=f"/api/player/video/remux?{params}",
            mime_type="video/mp4",
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            selected_audio_stream=selected_audio,
            preserves_video=True,
        )
    if not ffmpeg:
        raise HTTPException(422, "Video format is not browser playable and ffmpeg is unavailable")
    key = hls_key(path, selected_audio)
    playlist = hls_dir(key) / "index.m3u8"
    if not playlist.exists():
        start_hls_transcode(path, key, ffmpeg, selected_audio)
        if not wait_for_playlist(playlist):
            raise HTTPException(503, "Playback is still preparing")
    params = f"playback_id={quote(playback_id)}"
    if selected_audio is not None:
        params += f"&audio_stream={selected_audio}"
    return VideoPlaybackSource(
        mode="hls",
        url=f"/api/player/video/hls/{key}/index.m3u8?{params}",
        mime_type="application/vnd.apple.mpegurl",
        audio_tracks=audio_tracks,
        subtitle_tracks=subtitle_tracks,
        selected_audio_stream=selected_audio,
        preserves_video=False,
    )


def hls_playlist_response(
    path: Path,
    playback_id: str,
    key: str,
    ffmpeg: str | None,
    audio_stream: int | None = None,
) -> FileResponse:
    streams = probe_streams(path)
    selected_audio = select_audio_stream(audio_track_options(streams), audio_stream)
    if key != hls_key(path, selected_audio):
        raise HTTPException(403, "Invalid playback session")
    playlist = hls_dir(key) / "index.m3u8"
    if not playlist.exists():
        start_hls_transcode(path, key, ffmpeg, selected_audio)
        if not wait_for_playlist(playlist):
            raise HTTPException(503, "Playback is still preparing")
    return FileResponse(
        str(playlist),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache",
            "X-Playback-Id": playback_id,
        },
    )


def hls_segment_response(key: str, segment: str) -> FileResponse:
    if not HLS_SEGMENT_RE.match(segment):
        raise HTTPException(404, "Segment not found")
    segment_path = hls_dir(key) / segment
    if not segment_path.is_file():
        raise HTTPException(404, "Segment not found")
    return FileResponse(
        str(segment_path),
        media_type="video/mp2t",
        headers={"Cache-Control": "public, max-age=3600"},
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


async def remuxed_video_response(
    path: Path,
    request: Request,
    playback_id: str,
    audio_stream: int | None,
    ffmpeg: str | None,
):
    if not ffmpeg:
        raise HTTPException(422, "ffmpeg is unavailable")
    streams = probe_streams(path)
    if not can_remux_video_stream(streams):
        raise HTTPException(422, "Video cannot be remuxed without transcoding")
    selected_audio = select_audio_stream(audio_track_options(streams), audio_stream)
    cache_path = remuxed_video_cache_path(path, selected_audio)
    if not cache_path.exists():
        import asyncio

        await asyncio.to_thread(
            build_remuxed_video_cache,
            path,
            cache_path,
            ffmpeg,
            selected_audio,
            video_codec(streams),
        )
    return stream_file(cache_path, request, storage=local_storage)


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


def should_transcode_video(path: Path, ffmpeg: str | None) -> bool:
    if not ffmpeg:
        return False
    return not can_direct_play_video(path)


def can_direct_play_video(path: Path) -> bool:
    return path.suffix.lower() in DIRECT_VIDEO_EXTENSIONS


async def transcode_video(path: Path, request: Request, ffmpeg: str | None):
    if not ffmpeg:
        raise HTTPException(422, "Video format is not browser playable and ffmpeg is unavailable")
    cache_path = transcoded_video_cache_path(path)
    if not cache_path.exists():
        import asyncio

        await asyncio.to_thread(build_transcoded_video_cache, path, cache_path, ffmpeg)
    return stream_file(cache_path, request, storage=local_storage)


def transcoded_video_cache_path(path: Path) -> Path:
    stat = path.stat()
    key = sha256(f"{path}:{stat.st_size}:{stat.st_mtime_ns}:video-v1".encode()).hexdigest()
    return load_cli_config().paths.cache_dir / "player-video" / f"{key}.mp4"


def remuxed_video_cache_path(path: Path, audio_stream: int | None) -> Path:
    stat = path.stat()
    key = sha256(
        f"{path}:{stat.st_size}:{stat.st_mtime_ns}:remux-v2:{audio_stream}".encode()
    ).hexdigest()
    return load_cli_config().paths.cache_dir / "player-video-remux" / f"{key}.mp4"


def hls_key(path: Path, audio_stream: int | None = None) -> str:
    stat = path.stat()
    return sha256(
        f"{path.expanduser().resolve()}:{stat.st_size}:{stat.st_mtime_ns}:hls-v2:{audio_stream}".encode()
    ).hexdigest()


def hls_dir(key: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise HTTPException(404, "Playback session not found")
    return load_cli_config().paths.cache_dir / "player-video-hls" / key


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


def start_hls_transcode(source: Path, key: str, ffmpeg: str | None, audio_stream: int | None) -> None:
    if not ffmpeg:
        raise HTTPException(422, "ffmpeg is unavailable")
    directory = hls_dir(key)
    directory.mkdir(parents=True, exist_ok=True)
    process = HLS_PROCESSES.get(key)
    if process and process.poll() is None:
        return
    for file in directory.glob("seg_*.ts"):
        file.unlink(missing_ok=True)
    (directory / "index.m3u8").unlink(missing_ok=True)
    audio_map = f"0:{audio_stream}" if audio_stream is not None else "0:a:0?"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        audio_map,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "384k",
        "-ac",
        "2",
        "-f",
        "hls",
        "-hls_time",
        "4",
        "-hls_list_size",
        "0",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        str(directory / "seg_%05d.ts"),
        str(directory / "index.m3u8"),
    ]
    HLS_PROCESSES[key] = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_playlist(path: Path) -> bool:
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if path.exists() and path.stat().st_size > 0:
            return True
        time.sleep(0.2)
    return False


def build_transcoded_video_cache(source: Path, target: Path, ffmpeg: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp.mp4")
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
                "0:v:0",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        tmp.replace(target)
    except subprocess.CalledProcessError as exc:
        tmp.unlink(missing_ok=True)
        detail = exc.stderr.strip() or "Video transcode failed"
        raise HTTPException(500, detail) from exc


def build_remuxed_video_cache(
    source: Path,
    target: Path,
    ffmpeg: str,
    audio_stream: int | None,
    codec: str,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp.mp4")
    command = [
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
    ]
    if audio_stream is None:
        command.append("-an")
    else:
        command.extend(["-map", f"0:{audio_stream}"])
    command.extend(["-map_metadata", "0", "-c:v", "copy"])
    if codec in {"hevc", "h265"}:
        command.extend(["-tag:v", "hvc1"])
    if audio_stream is not None:
        command.extend(["-c:a", "aac", "-b:a", "384k"])
    command.extend(["-sn", "-movflags", "+faststart", str(tmp)])
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        tmp.replace(target)
    except subprocess.CalledProcessError as exc:
        tmp.unlink(missing_ok=True)
        detail = exc.stderr.strip() or "Video remux failed"
        raise HTTPException(500, detail)


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


def can_remux_video_stream(streams: list[dict[str, object]]) -> bool:
    return video_codec(streams) in REMUX_VIDEO_CODECS


def video_codec(streams: list[dict[str, object]]) -> str:
    for stream in streams:
        if stream.get("codec_type") == "video":
            return str(stream.get("codec_name") or "").lower()
    return ""


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
