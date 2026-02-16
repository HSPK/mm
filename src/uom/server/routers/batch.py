from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from uom.db.repository import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import BatchDeleteBody, BatchRatingBody, BatchTagBody, BatchTagRemoveBody

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("/tags")
async def batch_add_tags(
    request: Request,
    body: BatchTagBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = 0
    # Optimize? For now, simple loop async is fine for small batches.
    for mid in body.media_ids:
        # Check existence?
        m = await repo.get_media_by_id(mid)
        if not m:
            continue
        for name in body.tags:
            tag = await repo.get_or_create_tag(name)
            await repo.add_media_tag(mid, tag.id)  # type: ignore[arg-type]
        count += 1
    return {"status": "ok", "affected": count}


@router.post("/tags/remove")
async def batch_remove_tags(
    request: Request,
    body: BatchTagRemoveBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = 0
    for mid in body.media_ids:
        # Assuming we just need to try removal
        for name in body.tags:
            tag = await repo.get_tag_by_name(name)
            if tag and tag.id:
                await repo.remove_media_tag(mid, tag.id)
        count += 1
    # Cleanup
    await repo.delete_orphan_tags()
    return {"status": "ok", "affected": count}


@router.post("/rating")
async def batch_set_rating(
    request: Request,
    body: BatchRatingBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = 0
    for mid in body.media_ids:
        await repo.set_rating(mid, body.rating)
        count += 1
    return {"status": "ok", "affected": count}


@router.post("/delete")
async def batch_delete(
    request: Request,
    body: BatchDeleteBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    repo = get_repo(request)
    count = await repo.batch_soft_delete(body.media_ids)
    return {"status": "ok", "affected": count}
