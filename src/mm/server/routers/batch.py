from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import (
    BatchAffected,
    BatchDeleteBody,
    BatchMetadataBody,
    BatchRatingBody,
    BatchTagBody,
    BatchTagRemoveBody,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/tags", response_model=BatchAffected)
async def batch_add_tags(
    request: Request,
    body: BatchTagBody,
    _u: User | None = Depends(get_current_user),
) -> BatchAffected:
    count = await get_db(request).tag.bulk_add(body.media_ids, body.tags)
    return BatchAffected(affected=count)


@router.post("/tags/remove", response_model=BatchAffected)
async def batch_remove_tags(
    request: Request,
    body: BatchTagRemoveBody,
    _u: User | None = Depends(get_current_user),
) -> BatchAffected:
    count = await get_db(request).tag.bulk_remove(body.media_ids, body.tags)
    return BatchAffected(affected=count)


@router.post("/rating", response_model=BatchAffected)
async def batch_set_rating(
    request: Request,
    body: BatchRatingBody,
    _u: User | None = Depends(get_current_user),
) -> BatchAffected:
    count = await get_db(request).media.bulk_set_rating(body.media_ids, body.rating)
    return BatchAffected(affected=count)


@router.post("/delete", response_model=BatchAffected)
async def batch_delete(
    request: Request,
    body: BatchDeleteBody,
    _u: User | None = Depends(get_current_user),
) -> BatchAffected:
    count = await get_db(request).media.batch_soft_delete(body.media_ids)
    return BatchAffected(affected=count)


@router.post("/metadata", response_model=BatchAffected)
async def batch_update_metadata(
    request: Request,
    body: BatchMetadataBody,
    _u: User | None = Depends(get_current_user),
) -> BatchAffected:
    """Apply the same metadata patch (date/gps/location) to many media."""
    db = get_db(request)
    patch = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if k != "media_ids" and v is not None
    }
    if not patch or not body.media_ids:
        return BatchAffected(affected=0)
    affected = 0
    for mid in body.media_ids:
        result = await db.metadata.update(mid, **patch)
        if result is not None:
            affected += 1
    return BatchAffected(affected=affected)
