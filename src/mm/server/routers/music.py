from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import artwork_thumbnail, first_artwork_path
from mm.server.dependencies import get_current_user, get_db
from mm.server.music_catalog import (
    get_music_album,
    get_music_artist,
    list_music_albums,
    list_music_artists,
    list_music_tracks,
)
from mm.server.music_schemas import (
    MusicAlbum,
    MusicAlbumsResponse,
    MusicArtist,
    MusicArtistsResponse,
    MusicLyricsResource,
    MusicTracksResponse,
)
from mm.server.organizer_lyrics import local_lyrics_resource
from mm.server.organizer_paths import allowed_media_source_path

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/albums", response_model=MusicAlbumsResponse)
async def music_albums(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    query: str = "",
    artist_id: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicAlbumsResponse:
    return await list_music_albums(
        db,
        offset=offset,
        limit=limit,
        query=query,
        artist_id=artist_id,
    )


@router.get("/albums/{album_id}", response_model=MusicAlbum)
async def music_album(
    album_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicAlbum:
    album = await get_music_album(db, album_id)
    if album is None:
        raise HTTPException(404, "Music album not found")
    return album


@router.get("/tracks", response_model=MusicTracksResponse)
async def music_tracks(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    query: str = "",
    album_id: str = "",
    artist_id: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicTracksResponse:
    return await list_music_tracks(
        db,
        offset=offset,
        limit=limit,
        query=query,
        album_id=album_id,
        artist_id=artist_id,
    )


@router.get("/tracks/{playback_id}/lyrics", response_model=MusicLyricsResource)
async def music_lyrics(
    playback_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicLyricsResource:
    row = await _music_track_row(db, playback_id)
    media_path = _safe_music_path(row)
    lyrics, synced_lyrics, version = await asyncio.to_thread(
        local_lyrics_resource,
        media_path,
    )
    return MusicLyricsResource(
        playback_id=playback_id,
        lyrics=lyrics,
        synced_lyrics=synced_lyrics,
        version=version,
    )


@router.get("/artists", response_model=MusicArtistsResponse)
async def music_artists(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    query: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicArtistsResponse:
    return await list_music_artists(db, offset=offset, limit=limit, query=query)


@router.get("/artists/{artist_id}", response_model=MusicArtist)
async def music_artist(
    artist_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> MusicArtist:
    artist = await get_music_artist(db, artist_id)
    if artist is None:
        raise HTTPException(404, "Music artist not found")
    return artist


@router.get("/artwork/{playback_id}")
async def music_artwork(
    playback_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    artwork_path = await _music_artwork_path(db, playback_id)
    return FileResponse(str(artwork_path))


@router.get("/artwork/{playback_id}/thumbnail")
async def music_artwork_thumbnail(
    playback_id: str,
    size: int = Query(320, ge=64, le=1024),
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    artwork_path = await _music_artwork_path(db, playback_id)
    thumb_path = await asyncio.to_thread(artwork_thumbnail, artwork_path, size)
    if thumb_path is None:
        raise HTTPException(422, "Artwork thumbnail could not be generated")
    return FileResponse(
        str(thumb_path),
        media_type="image/webp",
        headers={"Cache-Control": load_cli_config().thumbnails.http_cache_control},
    )


async def _music_artwork_path(db: AsyncDBClient, playback_id: str) -> Path:
    row = await _music_track_row(db, playback_id)
    artwork_path = first_artwork_path(Path(row.path), "track")
    if artwork_path is None:
        raise HTTPException(404, "Music artwork not found")
    if not allowed_media_source_path(artwork_path):
        raise HTTPException(403, "Music artwork is outside configured media sources")
    return artwork_path


async def _music_track_row(db: AsyncDBClient, playback_id: str) -> OrganizerMediaModel:
    try:
        organizer_id = int(playback_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid playback id") from exc
    try:
        row = await db.objects.get(OrganizerMediaModel, id=organizer_id)
    except OrganizerMediaModel.DoesNotExist as exc:
        raise HTTPException(404, "Music track not found") from exc
    if row.source_kind != "music" or row.media_type != "track" or row.missing:
        raise HTTPException(404, "Music track not found")
    return row


def _safe_music_path(row: OrganizerMediaModel) -> Path:
    media_path = Path(row.path).expanduser().resolve()
    if not media_path.is_file():
        raise HTTPException(404, "Music file not found")
    if not allowed_media_source_path(media_path):
        raise HTTPException(403, "Music file is outside configured media sources")
    return media_path
