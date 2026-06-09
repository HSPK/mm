from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from mm.db.dto import User
from mm.library.settings import LibraryConfig
from mm.server.dependencies import get_current_user, get_db
from mm.server.schemas import RenameTagBody, StatusOk, TagStats
from mm.server.smart_albums import invalidate_smart_albums_cache

router = APIRouter(prefix="/api/tags", tags=["tags"])


def _library_id(request: Request) -> str | None:
    config: LibraryConfig | None = getattr(request.app.state, "config", None)
    return config.library_id if config else None


@router.get("", response_model=list[TagStats])
async def list_tags(
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> list[TagStats]:
    db = get_db(request)
    stats = await db.tag.stats()
    return [TagStats(id=i, name=n, count=c) for i, n, c in stats]


@router.put("/{tag_id}", response_model=StatusOk)
async def rename_tag(
    request: Request,
    tag_id: int,
    body: RenameTagBody,
    _u: User | None = Depends(get_current_user),
) -> StatusOk:
    db = get_db(request)
    await db.tag.rename(tag_id, body.name)
    invalidate_smart_albums_cache(_library_id(request))
    return StatusOk()


@router.delete("/{tag_id}", response_model=StatusOk)
async def delete_tag(
    request: Request,
    tag_id: int,
    _u: User | None = Depends(get_current_user),
) -> StatusOk:
    db = get_db(request)
    await db.tag.delete(tag_id)
    invalidate_smart_albums_cache(_library_id(request))
    return StatusOk()
