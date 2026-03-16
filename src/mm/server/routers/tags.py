from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from uom.db.dto import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import RenameTagBody

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = get_repo(request)
    stats = await repo.tag_stats()
    return [{"name": n, "count": c} for n, c in stats]


@router.put("/{tag_id}")
async def rename_tag(
    request: Request,
    tag_id: int,
    body: RenameTagBody,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    await repo.rename_tag(tag_id, body.name)
    return {"status": "ok"}


@router.delete("/{tag_id}")
async def delete_tag(
    request: Request,
    tag_id: int,
    _u: User | None = Depends(get_current_user),
) -> dict[str, str]:
    repo = get_repo(request)
    await repo.delete_tag(tag_id)
    return {"status": "ok"}
