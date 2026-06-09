from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import (
    CameraStats,
    GeoPoint,
    LibraryStats,
    MediaBrief,
    TagStats,
    TimelineEntry,
    TypeDistribution,
    serialize_media_brief,
)

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=LibraryStats)
async def get_stats(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> LibraryStats:
    db = get_db(request)
    total_files, total_size, type_dist, tag_stats, cameras = await asyncio.gather(
        db.media.count(),
        db.stats.total_size(),
        db.stats.type_distribution(),
        db.tag.stats(),
        db.stats.cameras(),
    )
    return LibraryStats(
        total_files=total_files,
        total_size=total_size,
        type_distribution=TypeDistribution.model_validate(type_dist or {}),
        tags=[TagStats(id=tid, name=n, count=c) for tid, n, c in tag_stats],
        cameras=[CameraStats.model_validate(c) for c in cameras],
    )


@router.get("/timeline", response_model=list[TimelineEntry])
async def get_timeline(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[TimelineEntry]:
    raw: list[dict[str, Any]] = await get_db(request).stats.timeline()
    return [TimelineEntry.model_validate(entry) for entry in raw]


@router.get("/cameras", response_model=list[CameraStats])
async def get_cameras(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[CameraStats]:
    return [CameraStats.model_validate(c) for c in await get_db(request).stats.cameras()]


@router.get("/random", response_model=list[MediaBrief])
async def get_random_media(
    request: Request,
    count: int = Query(20, ge=1, le=100),
    type: str | None = None,
    _u: User | None = Depends(get_current_user),
) -> list[MediaBrief]:
    db = get_db(request)
    items = await db.stats.random(count, type)
    return [serialize_media_brief(m) for m in items]


@router.get("/geo", response_model=list[GeoPoint])
async def get_geo(
    request: Request,
    limit: int = Query(2000, ge=1, le=10000),
    _u: User | None = Depends(get_current_user),
) -> list[GeoPoint]:
    """Return up to `limit` GPS-tagged media as compact map markers — single
    JOIN query, no pagination needed. Frontend Map view uses this."""
    return [
        GeoPoint.model_validate(p)
        for p in await get_db(request).stats.geo_media(limit=limit)
    ]
