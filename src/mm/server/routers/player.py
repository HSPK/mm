from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel, VideoProbeCacheModel, VideoStateModel
from mm.io import local_storage
from mm.server.dependencies import get_current_user, get_db, get_media_user
from mm.server.media_tickets import issue_media_ticket
from mm.server.player_video import (
    VideoPlaybackSource,
    invalidate_probe_cache,
    preview_frame_response,
    probe_streams,
    subtitle_response,
    video_playback_source,
)
from mm.server.utils import content_type_for, stream_file

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


class AudioPlaybackSource(BaseModel):
    url: str = ""
    mime_type: str = "application/octet-stream"
    directly_supported: bool = False
    known_unsupported: bool = False
    unsupported_reason: str = ""


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
    if media_path.suffix.lower() not in {".mp4", ".m4v", ".mov", ".webm", ".ogv"}:
        raise HTTPException(422, "Video is not directly playable; use /api/player/video/source")
    return stream_file(media_path, request, storage=local_storage)


@router.get("/video/source", response_model=VideoPlaybackSource)
async def player_video_source(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
    audio_stream: int | None = None,
    refresh: bool = False,
) -> VideoPlaybackSource:
    media_path = await _safe_video_playback_path(db, playback_id)
    streams = await _probe_streams_cached(db, media_path, refresh=refresh)
    return await asyncio.to_thread(
        video_playback_source, media_path, playback_id, _FFMPEG, audio_stream, streams
    )


async def _probe_streams_cached(
    db: AsyncDBClient, path: Path, *, refresh: bool
) -> list[dict[str, object]] | None:
    """Serve ffprobe stream metadata from the DB cache, re-probing only when the
    file changed (size/mtime) or a refresh is requested."""
    try:
        stat = path.stat()
    except OSError:
        return None
    key = str(path)

    if refresh:
        invalidate_probe_cache(path)
    else:
        cached = await _get_probe_cache_row(db, key)
        if (
            cached is not None
            and cached.size == stat.st_size
            and cached.mtime_ns == stat.st_mtime_ns
        ):
            try:
                parsed = json.loads(cached.streams)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [s for s in parsed if isinstance(s, dict)]

    streams = await asyncio.to_thread(probe_streams, path)
    if streams:
        await _store_probe_cache(db, key, stat.st_size, stat.st_mtime_ns, streams)
    return streams


async def _get_probe_cache_row(db: AsyncDBClient, path: str) -> VideoProbeCacheModel | None:
    try:
        return await db.objects.get(VideoProbeCacheModel, path=path)
    except VideoProbeCacheModel.DoesNotExist:
        return None


async def _store_probe_cache(
    db: AsyncDBClient, path: str, size: int, mtime_ns: int, streams: list[dict[str, object]]
) -> None:
    payload = json.dumps(streams)
    existing = await _get_probe_cache_row(db, path)
    if existing is not None:
        await db.objects.execute(
            VideoProbeCacheModel.update(
                size=size, mtime_ns=mtime_ns, streams=payload, updated_at=dt.datetime.now()
            ).where(VideoProbeCacheModel.id == existing.id)
        )
    else:
        await db.objects.create(
            VideoProbeCacheModel,
            path=path,
            size=size,
            mtime_ns=mtime_ns,
            streams=payload,
        )


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
    return await asyncio.to_thread(
        subtitle_response, media_path, playback_id, stream_index, _FFMPEG
    )


@router.get("/audio")
async def player_audio(
    request: Request,
    path: str = "",
    _u: User | None = Depends(get_media_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    media_path = (
        await _safe_audio_playback_path(db, playback_id) if playback_id else _safe_media_path(path)
    )
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio file")
    return stream_file(media_path, request, storage=local_storage)


@router.get("/audio/info")
async def player_audio_info(
    path: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    playback_id: str = "",
):
    row: OrganizerMediaModel | None = None
    if playback_id:
        row = await _organizer_media_by_playback_id(db, playback_id)
        media_path = await _safe_audio_playback_path(db, playback_id)
    else:
        media_path = _safe_media_path(path)
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio file")
    duration = row.audio_duration if row and row.audio_duration is not None else None
    if duration is None:
        duration = await asyncio.to_thread(_media_duration, media_path)
    return {"duration": duration}


@router.get("/audio/source", response_model=AudioPlaybackSource)
async def player_audio_source(
    request: Request,
    playback_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> AudioPlaybackSource:
    row = await _organizer_media_by_playback_id(db, playback_id)
    media_path = await _safe_audio_playback_path(db, playback_id)
    mime_type = row.audio_mime_type or content_type_for(media_path)
    source = audio_playback_source(media_path, playback_id, mime_type)
    if source.directly_supported:
        config = request.app.state.config
        ticket = issue_media_ticket(
            request.app.state.media_ticket_secret,
            library_id=config.library_id,
            playback_id=playback_id,
            ttl_seconds=6 * 60 * 60,
        )
        source.url = f"/api/player/audio?playback_id={playback_id}&ticket={ticket}"
    return source


def audio_playback_source(
    media_path: Path,
    playback_id: str,
    mime_type: str,
) -> AudioPlaybackSource:
    if media_path.suffix.lower() == ".wma":
        return AudioPlaybackSource(
            mime_type=mime_type,
            known_unsupported=True,
            unsupported_reason="WMA audio is not directly supported by browsers",
        )
    if media_path.suffix.lower() not in {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav"}:
        return AudioPlaybackSource(
            mime_type=mime_type,
            known_unsupported=True,
            unsupported_reason="This audio format is not known to be directly browser-playable",
        )
    return AudioPlaybackSource(
        url=f"/api/player/audio?playback_id={playback_id}",
        mime_type=mime_type,
        directly_supported=True,
    )


@router.get("/video/states", response_model=list[VideoStateResponse])
async def video_states(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> list[VideoStateResponse]:
    owner = _state_owner(_u)
    rows = await db.objects.fetchall(VideoStateModel.select().where(VideoStateModel.owner == owner))
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
    await db.objects.execute(VideoStateModel.update(**updates).where(VideoStateModel.id == row.id))
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
