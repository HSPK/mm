from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import artwork_path_by_kind, first_artwork_path
from mm.server.dependencies import get_current_user, get_db
from mm.server.file_manager import is_local_request, open_in_file_manager
from mm.server.organizer_paths import allowed_media_source_path
from mm.server.organizer_schemas import OrganizerItem
from mm.server.video_library import list_video_items

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoLibraryItemsResponse(BaseModel):
    items: list[OrganizerItem] = Field(default_factory=list)


class VideoArtworkBatchBody(BaseModel):
    playback_ids: list[str] = Field(default_factory=list)
    size: int = 320


class VideoArtworkBatchItem(BaseModel):
    playback_id: str
    thumb_url: str | None = None
    image_url: str | None = None


class VideoArtworkBatchResponse(BaseModel):
    items: list[VideoArtworkBatchItem] = Field(default_factory=list)


@router.get("/items", response_model=VideoLibraryItemsResponse)
async def video_items(
    kind: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> VideoLibraryItemsResponse:
    if kind not in {"movies", "tv"}:
        raise HTTPException(400, "Video kind must be movies or tv")
    return VideoLibraryItemsResponse(items=await list_video_items(db, kind))


@router.post("/reveal")
async def reveal_video_in_file_manager(
    request: Request,
    playback_id: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> dict[str, bool]:
    if not is_local_request(request):
        raise HTTPException(403, "Opening the file manager is only available on the local machine")
    row = await _video_library_row(db, playback_id)
    path = Path(row.path)
    if not allowed_media_source_path(path):
        raise HTTPException(403, "File is outside configured media sources")
    if not path.exists():
        raise HTTPException(404, "File not found")
    if not await asyncio.to_thread(open_in_file_manager, path, select=True):
        raise HTTPException(422, "Could not open the system file manager")
    return {"revealed": True}


@router.get("/artwork/image/item/{playback_id}")
async def video_artwork_image_for_item(
    playback_id: str,
    kind: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    return FileResponse(str(await _artwork_path_for_playback_id(db, playback_id, kind)))


@router.get("/artwork/thumb/item/{playback_id}")
async def video_artwork_thumb_for_item(
    playback_id: str,
    size: int = 320,
    kind: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    from mm.organizer.artwork_cache import artwork_thumbnail

    image_path = await _artwork_path_for_playback_id(db, playback_id, kind)
    thumb_path = await asyncio.to_thread(artwork_thumbnail, image_path, size)
    if thumb_path is None:
        raise HTTPException(422, "Artwork thumbnail could not be generated")
    return FileResponse(
        str(thumb_path),
        media_type="image/webp",
        headers={"Cache-Control": load_cli_config().thumbnails.http_cache_control},
    )


@router.post("/artwork/batch", response_model=VideoArtworkBatchResponse)
async def video_artwork_batch(
    body: VideoArtworkBatchBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> VideoArtworkBatchResponse:
    items: list[VideoArtworkBatchItem] = []
    for playback_id in dict.fromkeys(body.playback_ids):
        try:
            await _artwork_path_for_playback_id(db, playback_id)
        except HTTPException:
            items.append(VideoArtworkBatchItem(playback_id=playback_id))
            continue
        items.append(
            VideoArtworkBatchItem(
                playback_id=playback_id,
                thumb_url=f"/api/videos/artwork/thumb/item/{playback_id}?size={body.size}",
                image_url=f"/api/videos/artwork/image/item/{playback_id}",
            )
        )
    return VideoArtworkBatchResponse(items=items)


async def _artwork_path_for_playback_id(
    db: AsyncDBClient,
    playback_id: str,
    kind: str = "",
) -> Path:
    row = await _video_library_row(db, playback_id)
    if kind:
        artwork_path = artwork_path_by_kind(Path(row.path), row.media_type, kind)
    else:
        artwork_path = first_artwork_path(Path(row.path), row.media_type)
    if artwork_path is None:
        raise HTTPException(404, "Artwork not found")
    if not allowed_media_source_path(artwork_path):
        raise HTTPException(403, "Artwork is outside configured media sources")
    return artwork_path


async def _video_library_row(db: AsyncDBClient, playback_id: str) -> OrganizerMediaModel:
    try:
        video_id = int(playback_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid playback id") from exc
    try:
        row = await db.objects.get(OrganizerMediaModel, id=video_id)
    except OrganizerMediaModel.DoesNotExist as exc:
        raise HTTPException(404, "Playback item not found") from exc
    if row.media_type not in {"movie", "tv"}:
        raise HTTPException(400, "Playback id is not a video item")
    return row
