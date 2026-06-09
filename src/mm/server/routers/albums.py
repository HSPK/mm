from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import (
    AlbumActionResponse,
    AlbumMediaBody,
    AlbumSummary,
    CreateAlbumBody,
    CreatedAlbum,
    StatusMessage,
)

router = APIRouter(prefix="/api/albums", tags=["albums"])


@router.get("", response_model=list[AlbumSummary])
async def list_albums(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[AlbumSummary]:
    db = get_db(request)
    return [AlbumSummary.model_validate(a) for a in await db.album.list()]


@router.post("", response_model=CreatedAlbum)
async def create_album(
    request: Request,
    body: CreateAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> CreatedAlbum:
    db = get_db(request)
    return CreatedAlbum.model_validate(await db.album.create(body.name, body.description))


@router.delete("/{album_id}", response_model=StatusMessage)
async def delete_album(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> StatusMessage:
    db = get_db(request)
    ok = await db.album.delete(album_id)
    if not ok:
        raise HTTPException(404, "Album not found")
    return StatusMessage(message="ok")


@router.patch("/{album_id}", response_model=StatusMessage)
async def rename_album(
    request: Request,
    album_id: int,
    body: CreateAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> StatusMessage:
    db = get_db(request)
    ok = await db.album.rename(album_id, body.name)
    if not ok:
        raise HTTPException(404, "Album not found")
    return StatusMessage(message="ok")


@router.post("/{album_id}/media", response_model=AlbumActionResponse)
async def add_media_to_album(
    request: Request,
    album_id: int,
    body: AlbumMediaBody,
    _u: User | None = Depends(get_current_user),
) -> AlbumActionResponse:
    db = get_db(request)
    count = await db.album.add_media(album_id, body.media_ids)
    return AlbumActionResponse(message="added", affected=count)


@router.delete("/{album_id}/media", response_model=AlbumActionResponse)
async def remove_media_from_album(
    request: Request,
    album_id: int,
    body: AlbumMediaBody,
    _u: User | None = Depends(get_current_user),
) -> AlbumActionResponse:
    db = get_db(request)
    count = await db.album.remove_media(album_id, body.media_ids)
    return AlbumActionResponse(message="removed", affected=count)
