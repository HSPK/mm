from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from uom.db.dto import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import BatchDeleteBody, BatchRatingBody, BatchTagBody, BatchTagRemoveBody

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/tags")
async def batch_add_tags(
    request: Request,
    body: BatchTagBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    count = await get_repo(request).bulk_add_tags(body.media_ids, body.tags)
    return {"status": "ok", "affected": count}


@router.post("/tags/remove")
async def batch_remove_tags(
    request: Request,
    body: BatchTagRemoveBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    count = await get_repo(request).bulk_remove_tags(body.media_ids, body.tags)
    return {"status": "ok", "affected": count}


@router.post("/rating")
async def batch_set_rating(
    request: Request,
    body: BatchRatingBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    count = await get_repo(request).bulk_set_rating(body.media_ids, body.rating)
    return {"status": "ok", "affected": count}


@router.post("/delete")
async def batch_delete(
    request: Request,
    body: BatchDeleteBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    count = await get_repo(request).batch_soft_delete(body.media_ids)
    return {"status": "ok", "affected": count}
