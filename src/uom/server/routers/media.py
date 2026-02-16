from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from uom.db.repository import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import RatingBody, TagsBody, serialize_media, serialize_media_brief
from uom.server.thumbnail import get_thumbnail
from uom.server.utils import stream_file

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("")
async def list_media(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(60, ge=1, le=200),
    type: str | None = None,
    tag: str | None = None,
    camera: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "date_taken",
    order: str = "desc",
    search: str | None = None,
    min_rating: int | None = None,
    favorites_only: bool = False,
    lat: float | None = None,
    lon: float | None = None,
    radius: float | None = None,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    tag_list = [t.strip() for t in tag.split(",") if t.strip()] if tag else None
    items, total = await repo.query_media(
        page=page,
        per_page=per_page,
        media_type=type,
        tag_names=tag_list,
        camera=camera,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        order=order,
        search=search,
        min_rating=min_rating,
        favorites_only=favorites_only,
        lat=lat,
        lon=lon,
        radius=radius,
    )
    # Batch-fetch metadata for all items
    meta_map: dict[int, Any] = {}
    for m in items:
        if m.id:
            md = await repo.get_metadata(m.id)
            if md:
                meta_map[m.id] = md
    return {
        "items": [serialize_media_brief(m, meta_map.get(m.id)) for m in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/{media_id}")
async def get_media_detail(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    return await serialize_media(m, repo)


@router.get("/{media_id}/thumbnail")
async def get_thumbnail_file(
    request: Request,
    media_id: int,
    size: str = Query("md", pattern="^(sm|md|lg|xl)$"),
    _u: User | None = Depends(get_current_user),
) -> FileResponse:
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    # This is potentially blocking (CPU/IO), but short term OK or needs wrapper
    # Using run_in_threadpool if strictly async required,
    # but for now calling directly is fine unless getting huge traffic.
    thumb = get_thumbnail(m.path, media_id, size)
    if not thumb:
        raise HTTPException(404, "Thumbnail generation failed")

    return FileResponse(
        thumb,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/{media_id}/preview")
async def get_preview_image(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
) -> FileResponse:
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    # Generate or return xl preview (1080p typically)
    thumb = get_thumbnail(m.path, media_id, "xl")
    if not thumb:
        raise HTTPException(404, "Preview generation failed")

    return FileResponse(
        thumb,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/{media_id}/file")
async def get_media_file(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
):
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    fpath = Path(m.path)
    if not fpath.exists():
        raise HTTPException(404, "File not found on disk")

    return stream_file(fpath, request)


@router.put("/{media_id}/rating")
async def set_media_rating(
    request: Request,
    media_id: int,
    body: RatingBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    await repo.set_rating(media_id, body.rating)
    return {"status": "ok", "rating": max(0, min(5, body.rating))}


@router.post("/{media_id}/tags")
async def add_media_tags(
    request: Request,
    media_id: int,
    body: TagsBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    if not body.tags:
        raise HTTPException(400, "No tags provided")
    for name in body.tags:
        tag = await repo.get_or_create_tag(name)
        await repo.add_media_tag(media_id, tag.id)  # type: ignore[arg-type]
    return {"status": "ok"}


@router.delete("/{media_id}/tags/{tag_name}")
async def remove_media_tag(
    request: Request,
    media_id: int,
    tag_name: str,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    tag = await repo.get_tag_by_name(tag_name)
    if not tag or not tag.id:
        raise HTTPException(404, "Tag not found")
    await repo.remove_media_tag(media_id, tag.id)
    return {"status": "ok"}
