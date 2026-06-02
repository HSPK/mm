"""Smart Albums router — resolved list + CRUD for definitions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import SmartAlbumBody, SmartAlbumUpdateBody
from mm.server.smart_albums import build_smart_albums

router = APIRouter(prefix="/api/smart-albums", tags=["smart-albums"])


# ── Resolved list (consumed by the frontend) ──────────────


@router.get("")
async def get_smart_albums(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Return all smart album sections with covers resolved server-side."""
    db = get_db(request)
    return await build_smart_albums(db)


# ── Raw definitions CRUD ──────────────────────────────────


@router.get("/definitions")
async def list_definitions(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return all smart album definitions (including disabled) for admin."""
    db = get_db(request)
    return await db.smart_album.list_all()


@router.get("/definitions/{album_id}")
async def get_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    defn = await db.smart_album.get(album_id)
    if not defn:
        raise HTTPException(404, "Smart album not found")
    return defn


@router.post("/definitions", status_code=201)
async def create_definition(
    request: Request,
    body: SmartAlbumBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new smart album definition (user-created, is_system=0)."""
    db = get_db(request)
    data = body.model_dump()
    data["is_system"] = 0
    try:
        return await db.smart_album.create(data)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/definitions/{album_id}")
async def update_definition(
    request: Request,
    album_id: int,
    body: SmartAlbumUpdateBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Update an existing smart album definition."""
    db = get_db(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    result = await db.smart_album.update(album_id, data)
    if not result:
        raise HTTPException(404, "Smart album not found")
    return result


@router.delete("/definitions/{album_id}")
async def delete_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a non-system smart album definition."""
    db = get_db(request)
    ok = await db.smart_album.delete(album_id)
    if not ok:
        raise HTTPException(404, "Smart album not found or is a system album")
    return {"status": "ok"}


@router.patch("/definitions/{album_id}/toggle")
async def toggle_definition(
    request: Request,
    album_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Toggle enabled/disabled state of a smart album definition."""
    db = get_db(request)
    result = await db.smart_album.toggle(album_id)
    if not result:
        raise HTTPException(404, "Smart album not found")
    return result


@router.post("/definitions/reset")
async def reset_definitions(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete all smart album definitions and re-seed defaults."""
    db = get_db(request)
    count = await db.smart_album.reset()
    return {"status": "ok", "seeded": count}
