"""Smart Albums router — resolved list + CRUD for definitions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import (
    SmartAlbumBody,
    SmartAlbumDefinition,
    SmartAlbumResetResult,
    SmartAlbumUpdateBody,
    SmartAlbumsResponse,
    StatusOk,
)
from mm.server.smart_albums import build_smart_albums

router = APIRouter(prefix="/api/smart-albums", tags=["smart-albums"])


# ── Resolved list (consumed by the frontend) ──────────────


@router.get("", response_model=SmartAlbumsResponse)
async def get_smart_albums(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumsResponse:
    """Return all smart album sections with covers resolved server-side."""
    db = get_db(request)
    return SmartAlbumsResponse.model_validate(await build_smart_albums(db))


# ── Raw definitions CRUD ──────────────────────────────────


@router.get("/definitions", response_model=list[SmartAlbumDefinition])
async def list_definitions(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[SmartAlbumDefinition]:
    """Return all smart album definitions (including disabled) for admin."""
    db = get_db(request)
    rows = await db.smart_album.list_all()
    return [SmartAlbumDefinition.model_validate(r) for r in rows]


@router.get("/definitions/{album_id}", response_model=SmartAlbumDefinition)
async def get_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumDefinition:
    db = get_db(request)
    defn = await db.smart_album.get(album_id)
    if not defn:
        raise HTTPException(404, "Smart album not found")
    return SmartAlbumDefinition.model_validate(defn)


@router.post("/definitions", status_code=201, response_model=SmartAlbumDefinition)
async def create_definition(
    request: Request,
    body: SmartAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumDefinition:
    """Create a new smart album definition (user-created, is_system=0)."""
    db = get_db(request)
    data: dict[str, Any] = body.model_dump()
    data["is_system"] = 0
    try:
        result = await db.smart_album.create(data)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return SmartAlbumDefinition.model_validate(result)


@router.put("/definitions/{album_id}", response_model=SmartAlbumDefinition)
async def update_definition(
    request: Request,
    album_id: int,
    body: SmartAlbumUpdateBody,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumDefinition:
    """Update an existing smart album definition."""
    db = get_db(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await db.smart_album.update(album_id, data)
    if not result:
        raise HTTPException(404, "Smart album not found")
    return SmartAlbumDefinition.model_validate(result)


@router.delete("/definitions/{album_id}", response_model=StatusOk)
async def delete_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> StatusOk:
    """Delete a non-system smart album definition."""
    db = get_db(request)
    ok = await db.smart_album.delete(album_id)
    if not ok:
        raise HTTPException(404, "Smart album not found or is a system album")
    return StatusOk()


@router.patch("/definitions/{album_id}/toggle", response_model=SmartAlbumDefinition)
async def toggle_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumDefinition:
    """Toggle enabled/disabled state of a smart album definition."""
    db = get_db(request)
    result = await db.smart_album.toggle(album_id)
    if not result:
        raise HTTPException(404, "Smart album not found")
    return SmartAlbumDefinition.model_validate(result)


@router.post("/definitions/reset", response_model=SmartAlbumResetResult)
async def reset_definitions(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> SmartAlbumResetResult:
    """Delete all smart album definitions and re-seed defaults."""
    db = get_db(request)
    count = await db.smart_album.reset()
    return SmartAlbumResetResult(seeded=count)
