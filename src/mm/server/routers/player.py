from __future__ import annotations

import asyncio
import datetime as dt
import shutil
import subprocess
import uuid
from hashlib import sha256
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel, VideoStateModel
from mm.io import local_storage
from mm.server.dependencies import get_current_user, get_db
from mm.server.player_video import (
    VideoPlaybackSource,
    hls_playlist_response,
    hls_segment_response,
    preview_frame_response,
    remuxed_video_response,
    should_transcode_video,
    subtitle_response,
    transcode_video,
    video_playback_source,
)
from mm.server.utils import stream_file

router = APIRouter(prefix="/api/player", tags=["player"])

_FFMPEG = shutil.which("ffmpeg")
_FFPROBE = shutil.which("ffprobe")


class VideoStateResponse(BaseModel):
    playback_id: str
    favorite: bool = False
    watched: bool = False
    notes: str = ""
    progress: float = 0.0
    duration: float = 0.0
    updated_at: str = ""


class VideoStatePatch(BaseModel):
    playback_id: str
    favorite: bool | None = None
    watched: bool | None = None
    notes: str | None = None
    progress: float | None = None
    duration: float | None = None


@router.get("/file")
async def player_file(
    request: Request,
    path: str,
    _u: User | None = Depends(get_current_user),
):
    media_path = _safe_media_path(path)
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS | VIDEO_EXTENSIONS:
        raise HTTPException(400, "Unsupported media file")
    return stream_file(media_path, request, storage=local_storage)


@router.get("/video")
async def player_video(
    request: Request,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    media_path = await _safe_video_playback_path(db, playback_id)
    if should_transcode_video(media_path, _FFMPEG):
        return await transcode_video(media_path, request, _FFMPEG)
    return stream_file(media_path, request, storage=local_storage)


@router.get("/video/source", response_model=VideoPlaybackSource)
async def player_video_source(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    audio_stream: int | None = None,
) -> VideoPlaybackSource:
    media_path = await _safe_video_playback_path(db, playback_id)
    return await asyncio.to_thread(video_playback_source, media_path, playback_id, _FFMPEG, audio_stream)


@router.get("/video/remux")
async def player_video_remux(
    request: Request,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    audio_stream: int | None = None,
):
    media_path = await _safe_video_playback_path(db, playback_id)
    return await remuxed_video_response(media_path, request, playback_id, audio_stream, _FFMPEG)


@router.get("/video/hls/{key}/index.m3u8")
async def player_video_hls_playlist(
    key: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    audio_stream: int | None = None,
):
    media_path = await _safe_video_playback_path(db, playback_id)
    return hls_playlist_response(media_path, playback_id, key, _FFMPEG, audio_stream)


@router.get("/video/hls/{key}/{segment}")
async def player_video_hls_segment(
    key: str,
    segment: str,
    _u: User | None = Depends(get_current_user),
):
    return hls_segment_response(key, segment)


@router.get("/video/info")
async def player_video_info(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    media_path = await _safe_video_playback_path(db, playback_id)
    return {"duration": _media_duration(media_path)}


@router.get("/video/preview")
async def player_video_preview(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    time: float = 0.0,
):
    media_path = await _safe_video_playback_path(db, playback_id)
    return await asyncio.to_thread(preview_frame_response, media_path, playback_id, time, _FFMPEG)


@router.get("/video/subtitle")
async def player_video_subtitle(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    stream_index: int = 0,
):
    media_path = await _safe_video_playback_path(db, playback_id)
    return await asyncio.to_thread(subtitle_response, media_path, playback_id, stream_index, _FFMPEG)


@router.get("/audio")
async def player_audio(
    request: Request,
    path: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    media_path = (
        await _safe_audio_playback_path(db, playback_id)
        if playback_id
        else _safe_media_path(path)
    )
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio file")
    if _should_transcode_audio(media_path):
        return _transcode_audio(media_path, request)
    return stream_file(media_path, request, storage=local_storage)


@router.get("/audio/info")
async def player_audio_info(
    path: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    media_path = (
        await _safe_audio_playback_path(db, playback_id)
        if playback_id
        else _safe_media_path(path)
    )
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio file")
    return {"duration": _media_duration(media_path)}


@router.get("/video/states", response_model=list[VideoStateResponse])
async def video_states(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> list[VideoStateResponse]:
    owner = _state_owner(_u)
    rows = await db.objects.fetchall(
        VideoStateModel.select().where(VideoStateModel.owner == owner)
    )
    return [
        _video_state_response(row, playback_id)
        for row in rows
        if (playback_id := await _playback_id_for_path(db, row.path))
    ]


@router.get("/video/state", response_model=VideoStateResponse)
async def video_state(
    playback_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> VideoStateResponse:
    media_path = await _safe_video_playback_path(db, playback_id)
    row = await _video_state_row(db, _state_owner(_u), str(media_path), create=False)
    if row is None:
        return _empty_video_state(playback_id)
    return _video_state_response(row, playback_id)


@router.patch("/video/state", response_model=VideoStateResponse)
async def update_video_state(
    body: VideoStatePatch,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> VideoStateResponse:
    media_path = await _safe_video_playback_path(db, body.playback_id)
    row = await _video_state_row(db, _state_owner(_u), str(media_path), create=True)
    updates = {
        "updated_at": dt.datetime.now(),
    }
    if "favorite" in body.model_fields_set:
        updates["favorite"] = 1 if body.favorite else 0
    if "watched" in body.model_fields_set:
        updates["watched"] = 1 if body.watched else 0
    if "notes" in body.model_fields_set:
        updates["notes"] = body.notes or ""
    if "progress" in body.model_fields_set:
        updates["progress"] = max(0.0, float(body.progress or 0))
    if "duration" in body.model_fields_set:
        updates["duration"] = max(0.0, float(body.duration or 0))
    await db.objects.execute(
        VideoStateModel.update(**updates).where(VideoStateModel.id == row.id)
    )
    return _video_state_response(
        await db.objects.get(VideoStateModel, id=row.id),
        body.playback_id,
    )


def _safe_media_path(path: str) -> Path:
    media_path = Path(path).expanduser().resolve()
    if not media_path.is_file():
        raise HTTPException(404, "Media file not found")
    if not _is_allowed_media_source_path(media_path):
        raise HTTPException(403, "Media file is outside configured media sources")
    return media_path


def _safe_video_path(path: str) -> Path:
    media_path = _safe_media_path(path)
    if media_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise HTTPException(400, "Unsupported video file")
    return media_path


async def _safe_video_playback_path(db: AsyncDBClient, playback_id: str) -> Path:
    row = await _organizer_media_by_playback_id(db, playback_id)
    media_path = _safe_video_path(row.path)
    if row.media_type not in {"movie", "tv"}:
        raise HTTPException(400, "Playback id is not a video item")
    return media_path


async def _safe_audio_playback_path(db: AsyncDBClient, playback_id: str) -> Path:
    row = await _organizer_media_by_playback_id(db, playback_id)
    media_path = _safe_media_path(row.path)
    if row.media_type != "track":
        raise HTTPException(400, "Playback id is not an audio track")
    return media_path


async def _organizer_media_by_playback_id(
    db: AsyncDBClient,
    playback_id: str,
) -> OrganizerMediaModel:
    try:
        organizer_id = int(playback_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid playback id") from exc
    try:
        return await db.objects.get(OrganizerMediaModel, id=organizer_id)
    except OrganizerMediaModel.DoesNotExist as exc:
        raise HTTPException(404, "Playback item not found") from exc


def _state_owner(user: User | None) -> str:
    return user.username if user else "global"


async def _video_state_row(
    db: AsyncDBClient,
    owner: str,
    path: str,
    *,
    create: bool,
) -> VideoStateModel | None:
    try:
        return await db.objects.get(VideoStateModel, owner=owner, path=path)
    except VideoStateModel.DoesNotExist:
        if not create:
            return None
        return await db.objects.create(VideoStateModel, owner=owner, path=path)


def _empty_video_state(playback_id: str) -> VideoStateResponse:
    return VideoStateResponse(playback_id=playback_id)


def _video_state_response(row: VideoStateModel, playback_id: str) -> VideoStateResponse:
    return VideoStateResponse(
        playback_id=playback_id,
        favorite=bool(row.favorite),
        watched=bool(row.watched),
        notes=row.notes or "",
        progress=float(row.progress or 0),
        duration=float(row.duration or 0),
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


async def _playback_id_for_path(db: AsyncDBClient, path: str) -> str | None:
    try:
        row = await db.objects.get(OrganizerMediaModel, path=path)
    except OrganizerMediaModel.DoesNotExist:
        return None
    return str(row.id) if row.id is not None else None


def _is_allowed_media_source_path(path: Path) -> bool:
    cfg = load_cli_config()
    roots = [
        Path(source).expanduser().resolve()
        for sources in cfg.organizer.media_sources.values()
        for source in sources
    ]
    return any(_is_relative_to(path, root) for root in roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _should_transcode_audio(path: Path) -> bool:
    if not _FFMPEG:
        return False
    return path.suffix.lower() in {".flac", ".aiff", ".wma", ".ape", ".alac"}


def _media_duration(path: Path) -> float | None:
    if not _FFPROBE:
        return None
    try:
        result = subprocess.run(
            [
                _FFPROBE,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def _transcode_audio(path: Path, request: Request):
    if not _FFMPEG:
        raise HTTPException(500, "ffmpeg is not available")
    cache_path = _transcoded_cache_path(path)
    if not cache_path.exists():
        _build_transcoded_cache(path, cache_path)
    return stream_file(cache_path, request, storage=local_storage)


def _transcoded_cache_path(path: Path) -> Path:
    stat = path.stat()
    key = sha256(f"{path}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()
    return load_cli_config().paths.cache_dir / "player-audio" / f"{key}.mp3"


def _build_transcoded_cache(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp")
    try:
        subprocess.run(
            [
                _FFMPEG,
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-f",
                "mp3",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        tmp.replace(target)
    except subprocess.CalledProcessError as exc:
        tmp.unlink(missing_ok=True)
        detail = exc.stderr.strip() or "Audio transcode failed"
        raise HTTPException(500, detail) from exc
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(500, "Audio transcode failed") from exc
