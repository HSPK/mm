from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import RenameTagBody

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    db = get_db(request)
    stats = await db.tag.stats()
    return [{"name": n, "count": c} for n, c in stats]


@router.put("/{tag_id}")
async def rename_tag(
    request: Request,
    tag_id: int,
    body: RenameTagBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    await db.tag.rename(tag_id, body.name)
    return {"status": "ok"}


@router.delete("/{tag_id}")
async def delete_tag(
    request: Request,
    tag_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    db = get_db(request)
    await db.tag.delete(tag_id)
    return {"status": "ok"}
