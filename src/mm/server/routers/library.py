"""Library management — switch between library databases."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.config import get_config
from mm.db.backend import DatabaseTarget
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.io import local_storage
from mm.library.settings import LibraryConfig
from mm.server.dependencies import (
    get_current_user,
    get_db,
    invalidate_media_path_cache,
    invalidate_token_cache,
)
from mm.server.schemas import (
    LibraryInfo,
    SwitchLibraryBody,
    SwitchLibraryResponse,
)

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=LibraryInfo)
async def get_current_library(
    request: Request,
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> LibraryInfo:
    """Return info about the currently active library."""
    db_path = str(getattr(request.app.state, "db_path", ""))
    if not db_path:
        return LibraryInfo(db_path="", name="default", library_id="")
    target = DatabaseTarget.from_value(db_path)
    config = await db.library_config.get()
    return LibraryInfo(
        db_path=target.display,
        name=target.local_path.parent.name if target.local_path else "postgres",
        library_id=config.library_id,
    )


@router.get("/recent", response_model=list[LibraryInfo])
async def list_recent_libraries(
    user: User | None = Depends(get_current_user),
) -> list[LibraryInfo]:
    """Return the list of recently used library paths."""
    raw = os.environ.get("MM_LIBRARIES", "")
    current = os.environ.get("MM_DB", "mm.db")
    paths: list[str] = [p.strip() for p in raw.split(";") if p.strip()]
    if current and current not in paths:
        paths.insert(0, current)

    result: list[LibraryInfo] = []
    for p in paths:
        target = DatabaseTarget.from_value(p)
        if not target.is_local_file or local_storage.exists(target.local_path):
            result.append(
                LibraryInfo(
                    db_path=target.display,
                    name=target.local_path.parent.name
                    if target.local_path and target.local_path.parent != target.local_path
                    else "postgres",
                )
            )
    return result


@router.post("/switch", response_model=SwitchLibraryResponse)
async def switch_library(
    body: SwitchLibraryBody,
    request: Request,
    user: User | None = Depends(get_current_user),
) -> SwitchLibraryResponse:
    """Switch the active library database."""
    target = DatabaseTarget.from_value(body.db_path)

    if target.is_local_file and target.local_path and local_storage.is_dir(target.local_path):
        target = DatabaseTarget.from_value(target.local_path / get_config().import_.db_name)

    if target.is_local_file and target.local_path and not local_storage.exists(target.local_path):
        raise HTTPException(status_code=404, detail=f"Database not found: {target.display}")

    if target.is_local_file and target.local_path and not local_storage.is_file(target.local_path):
        raise HTTPException(status_code=400, detail=f"Not a file: {target.display}")

    resolved = target.display

    new_db = AsyncDBClient(resolved)
    await new_db.connect()
    await new_db.init_db()

    request.app.state.db = new_db
    request.app.state.db_path = resolved
    request.app.state.config = await new_db.library_config.get()
    os.environ["MM_DB"] = resolved

    invalidate_token_cache()
    invalidate_media_path_cache()

    return SwitchLibraryResponse(
        db_path=resolved,
        name=target.local_path.parent.name if target.local_path else "postgres",
        message="Library switched successfully",
    )


# ── Library config (key-value settings stored in DB) ──────


@router.get("/config", response_model=dict[str, str])
async def get_library_config(
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Return all library config key-value pairs."""
    return (await db.library_config.get()).model_dump(mode="json")


@router.put("/config", response_model=dict[str, str])
async def update_library_config(
    body: dict[str, str],
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Update one or more library config keys."""
    current = (await db.library_config.get()).model_dump(mode="json")
    config = LibraryConfig.model_validate({**current, **body})
    await db.library_config.set(config)
    return config.model_dump(mode="json")
