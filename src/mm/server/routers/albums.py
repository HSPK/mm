from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from uom.db.dto import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import AlbumMediaBody, CreateAlbumBody

router = APIRouter(prefix="/api/albums", tags=["albums"])


@router.get("")
async def list_albums(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = get_repo(request)
    return await repo.list_albums()


@router.post("")
async def create_album(
    request: Request,
    body: CreateAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    return await repo.create_album(body.name, body.description)


@router.delete("/{album_id}")
async def delete_album(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    ok = await repo.delete_album(album_id)
    if not ok:
        raise HTTPException(404, "Album not found")
    return {"status": "ok"}


@router.patch("/{album_id}")
async def rename_album(
    request: Request,
    album_id: int,
    body: CreateAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    ok = await repo.rename_album(album_id, body.name)
    if not ok:
        raise HTTPException(404, "Album not found")
    return {"status": "ok"}


@router.post("/{album_id}/media")
async def add_media_to_album(
    request: Request,
    album_id: int,
    body: AlbumMediaBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = await repo.add_media_to_album(album_id, body.media_ids)
    return {"status": "ok", "added": count}


@router.delete("/{album_id}/media")
async def remove_media_from_album(
    request: Request,
    album_id: int,
    body: AlbumMediaBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = await repo.remove_media_from_album(album_id, body.media_ids)
    return {"status": "ok", "removed": count}
