from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import serialize_media_brief

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    db = get_db(request)
    total_files, total_size, type_dist, tag_stats, cameras = await asyncio.gather(
        db.media.count(),
        db.stats.total_size(),
        db.stats.type_distribution(),
        db.tag.stats(),
        db.stats.cameras(),
    )
    return {
        "total_files": total_files,
        "total_size": total_size,
        "type_distribution": type_dist,
        "tags": [{"name": n, "count": c} for n, c in tag_stats],
        "cameras": cameras,
    }


@router.get("/timeline")
async def get_timeline(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    # Sync db returned list of dicts. Async db does too.
    return await get_db(request).stats.timeline()


@router.get("/cameras")
async def get_cameras(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await get_db(request).stats.cameras()


@router.get("/random")
async def get_random_media(
    request: Request,
    count: int = Query(20, ge=1, le=100),
    type: str | None = None,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    db = get_db(request)
    items = await db.stats.random(count, type)
    return [serialize_media_brief(m) for m in items]
