from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from uom.db.repository import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import serialize_media_brief

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)

    total_files = await repo.get_total_media_count()
    total_size = await repo.total_size()
    type_dist = await repo.type_distribution()
    tag_stats = await repo.tag_stats()
    cameras = await repo.cameras()

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
    # Sync repo returned list of dicts. Async repo does too.
    return await get_repo(request).timeline()


@router.get("/cameras")
async def get_cameras(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await get_repo(request).cameras()


@router.get("/random")
async def get_random_media(
    request: Request,
    count: int = Query(20, ge=1, le=100),
    type: str | None = None,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = get_repo(request)
    items = await repo.get_random(count, type)
    return [serialize_media_brief(m) for m in items]
