"""Library management — switch between library databases."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.config import DEFAULT_DB_NAME
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
from mm.server.schemas import SwitchLibraryBody

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("")
async def get_current_library(
    request: Request,
    user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Return info about the currently active library."""
    db_path = str(getattr(request.app.state, "db_path", ""))
    return {
        "db_path": db_path,
        "name": Path(db_path).parent.name if "/" in db_path or "\\" in db_path else "default",
    }


@router.get("/recent")
async def list_recent_libraries(
    user: User | None = Depends(get_current_user),
) -> list[dict[str, str]]:
    """Return the list of recently used library paths."""
    raw = os.environ.get("MM_LIBRARIES", "")
    current = os.environ.get("MM_DB", "mm.db")
    paths: list[str] = [p.strip() for p in raw.split(";") if p.strip()]
    if current and current not in paths:
        paths.insert(0, current)

    result = []
    for p in paths:
        pp = Path(p)
        if local_storage.exists(pp):
            result.append(
                {
                    "db_path": str(pp.resolve()),
                    "name": pp.parent.name if pp.parent != pp else "default",
                }
            )
    return result


@router.post("/switch")
async def switch_library(
    body: SwitchLibraryBody,
    request: Request,
    user: User | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Switch the active library database.

    The db_path can be either:
    - A direct path to a .db file
    - A directory path (will look for mm.db inside it)
    """
    target = Path(body.db_path)

    # If a directory is given, look for mm.db inside
    if local_storage.is_dir(target):
        target = target / DEFAULT_DB_NAME

    if not local_storage.exists(target):
        raise HTTPException(status_code=404, detail=f"Database not found: {target}")

    if not local_storage.is_file(target):
        raise HTTPException(status_code=400, detail=f"Not a file: {target}")

    resolved = str(target.resolve())

    # Swap the database client on the app
    new_db = AsyncDBClient(resolved)
    await new_db.connect()
    await new_db.init_db()

    request.app.state.db = new_db
    request.app.state.db_path = resolved
    request.app.state.config = await new_db.library_config.get()
    os.environ["MM_DB"] = resolved

    # Invalidate caches
    invalidate_token_cache()
    invalidate_media_path_cache()

    return {
        "db_path": resolved,
        "name": target.parent.name,
        "message": "Library switched successfully",
    }


# ── Library config (key-value settings stored in DB) ──────


@router.get("/config")
async def get_library_config(
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Return all library config key-value pairs."""
    return (await db.library_config.get()).model_dump(mode="json")


@router.put("/config")
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
