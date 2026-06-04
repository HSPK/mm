from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from mm.db.dto import User
from mm.io import local_storage
from mm.media.thumbnails import get_thumbnail
from mm.server.dependencies import (
    get_current_user,
    get_db,
    get_library_config,
    get_media_path,
    get_thumb_cache_dir,
)
from mm.server.schemas import (
    RatingBody,
    TagsBody,
    UpdateMetadataBody,
    serialize_media,
    serialize_media_brief,
)
from mm.server.utils import stream_file
from mm.utils.paths import resolve_media_path

router = APIRouter(prefix="/api/media", tags=["media"])

# ── Cache headers ──
_THUMB_CACHE_CONTROL = "public, max-age=31536000, immutable"


def _make_etag(thumb_path: Path) -> str:
    st = local_storage.stat(thumb_path)
    return f'W/"{hashlib.md5(f"{st.st_mtime_ns}-{st.st_size}".encode()).hexdigest()[:16]}"'


def _check_not_modified(request: Request, etag: str) -> Response | None:
    inm = request.headers.get("if-none-match")
    if inm and etag in inm:
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": _THUMB_CACHE_CONTROL},
        )
    return None


async def _serve_thumb(request: Request, media_id: int, size: str) -> Response:
    """Generate and serve a thumbnail/preview with ETag + 304 support."""
    media_path = await get_media_path(request, media_id)
    cache_dir = get_thumb_cache_dir(request)
    thumb = await run_in_threadpool(get_thumbnail, media_path, media_id, size, cache_dir)
    if not thumb:
        raise HTTPException(404, "Thumbnail generation failed")
    etag = _make_etag(thumb)
    not_modified = _check_not_modified(request, etag)
    if not_modified:
        return not_modified
    return FileResponse(
        thumb,
        media_type="image/webp",
        headers={"Cache-Control": _THUMB_CACHE_CONTROL, "ETag": etag},
    )


@router.get("")
async def list_media(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(60, ge=1, le=5000),
    type: str | None = None,
    tag: str | None = None,
    camera: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_ranges: str | None = None,
    sort: str = "date_taken",
    order: str = "desc",
    search: str | None = None,
    min_rating: int | None = None,
    favorites_only: bool = False,
    lat: float | None = None,
    lon: float | None = None,
    radius: float | None = None,
    has_location: bool = False,
    no_date: bool = False,
    deleted: bool = False,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    tag_list = [t.strip() for t in tag.split(",") if t.strip()] if tag else None

    # Parse date_ranges from JSON string
    parsed_date_ranges: list[list[str]] | None = None
    if date_ranges:
        try:
            parsed_date_ranges = json.loads(date_ranges)
        except (json.JSONDecodeError, TypeError):
            parsed_date_ranges = None

    items, total = await db.media.query(
        page=page,
        per_page=per_page,
        media_type=type,
        tag_names=tag_list,
        camera=camera,
        date_from=date_from,
        date_to=date_to,
        date_ranges=parsed_date_ranges,
        sort=sort,
        order=order,
        search=search,
        min_rating=min_rating,
        favorites_only=favorites_only,
        lat=lat,
        lon=lon,
        radius=radius,
        has_location=has_location,
        no_date=no_date,
        deleted=deleted,
    )
    # Batch-fetch metadata for all items
    meta_map: dict[int, Any] = {}
    media_ids = [m.id for m in items if m.id]
    if media_ids:
        meta_map = await db.metadata.get_for_ids(media_ids)
    return {
        "items": [serialize_media_brief(m, meta_map.get(m.id)) for m in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/trash")
async def list_trash(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    db = get_db(request)
    items = await db.media.list_trash()
    return [serialize_media_brief(m) for m in items]


@router.delete("/trash")
async def empty_trash(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    deleted = await db.media.empty_trash()
    return {"status": "ok", "deleted": deleted}


@router.get("/{media_id}")
async def get_media_detail(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    return await serialize_media(m, db)


@router.get("/{media_id}/thumbnail")
async def get_thumbnail_file(
    request: Request,
    media_id: int,
    size: str = Query("md", pattern="^(sm|md|lg|xl)$"),
    _u: User | None = Depends(get_current_user),
):
    return await _serve_thumb(request, media_id, size)


@router.get("/{media_id}/preview")
async def get_preview_image(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
):
    return await _serve_thumb(request, media_id, "xl")


@router.get("/{media_id}/file")
async def get_media_file(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
):
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    config = get_library_config(request)
    fpath = Path(resolve_media_path(m.path, config.library_root))
    if not local_storage.exists(fpath):
        raise HTTPException(404, "File not found on disk")

    return stream_file(fpath, request)


@router.put("/{media_id}/rating")
async def set_media_rating(
    request: Request,
    media_id: int,
    body: RatingBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    await db.media.set_rating(media_id, body.rating)
    return {"status": "ok", "rating": max(0, min(5, body.rating))}


@router.post("/{media_id}/tags")
async def add_media_tags(
    request: Request,
    media_id: int,
    body: TagsBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")
    if not body.tags:
        raise HTTPException(400, "No tags provided")
    for name in body.tags:
        tag = await db.tag.get_or_create(name)
        await db.tag.add_media(media_id, tag.id)  # type: ignore[arg-type]
    return {"status": "ok"}


@router.delete("/{media_id}/tags/{tag_name}")
async def remove_media_tag(
    request: Request,
    media_id: int,
    tag_name: str,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    tag = await db.tag.get_by_name(tag_name)
    if not tag or not tag.id:
        raise HTTPException(404, "Tag not found")
    await db.tag.remove_media(media_id, tag.id)
    return {"status": "ok"}


@router.patch("/{media_id}/metadata")
async def update_media_metadata(
    request: Request,
    media_id: int,
    body: UpdateMetadataBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    # Filter out None values from body
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}

    md = await db.metadata.update(media_id, **updates)
    if not md:
        raise HTTPException(500, "Failed to update metadata")

    return await serialize_media(m, db)


@router.delete("/{media_id}")
async def delete_media(
    request: Request,
    media_id: int,
    permanent: bool = Query(False, description="Permanently delete instead of trash"),
    delete_file: bool = Query(False, description="Also delete the file from disk"),
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    if permanent:
        if delete_file:
            config = get_library_config(request)
            fpath = Path(resolve_media_path(m.path, config.library_root))
            if local_storage.exists(fpath):
                local_storage.delete_file(fpath)
        await db.media.delete(media_id)
    else:
        await db.media.soft_delete(media_id)

    return {"status": "ok"}


@router.post("/{media_id}/restore")
async def restore_media(
    request: Request,
    media_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    ok = await db.media.restore(media_id)
    if not ok:
        raise HTTPException(404, "Media not found in trash")
    return {"status": "ok"}
