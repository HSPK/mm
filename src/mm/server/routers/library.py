"""Library management — switch between library databases."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from mm.config import DEFAULT_DB_NAME
from mm.db.async_repository import AsyncRepository
from mm.db.dto import User
from mm.server.dependencies import (
    get_current_user,
    get_repo,
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
        "name": Path(db_path).parent.name
        if "/" in db_path or "\\" in db_path
        else "default",
    }


@router.get("/recent")
async def list_recent_libraries(
    user: User | None = Depends(get_current_user),
) -> list[dict[str, str]]:
    """Return the list of recently used library paths."""
    raw = os.environ.get("UOM_LIBRARIES", "")
    current = os.environ.get("UOM_DB", "uom.db")
    paths: list[str] = [p.strip() for p in raw.split(";") if p.strip()]
    if current and current not in paths:
        paths.insert(0, current)

    result = []
    for p in paths:
        pp = Path(p)
        if pp.exists():
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
    - A directory path (will look for uom.db inside it)
    """
    target = Path(body.db_path)

    # If a directory is given, look for uom.db inside
    if target.is_dir():
        target = target / DEFAULT_DB_NAME

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Database not found: {target}")

    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {target}")

    resolved = str(target.resolve())

    # Swap the repository on the app
    new_repo = AsyncRepository(resolved)
    await new_repo.connect()
    await new_repo.init_db()

    request.app.state.repo = new_repo
    request.app.state.db_path = resolved
    request.app.state.library_root = str(Path(resolved).parent)
    os.environ["UOM_DB"] = resolved

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
    repo: AsyncRepository = Depends(get_repo),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Return all library config key-value pairs."""
    cfg = await repo.get_all_config()
    # Always include import_template even if not yet stored
    if "import_template" not in cfg:
        from mm.config import DEFAULT_IMPORT_TEMPLATE

        cfg["import_template"] = DEFAULT_IMPORT_TEMPLATE
    return cfg


@router.put("/config")
async def update_library_config(
    body: dict[str, str],
    repo: AsyncRepository = Depends(get_repo),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Update one or more library config keys."""
    for key, value in body.items():
        await repo.set_config(key, value)
    return await repo.get_all_config()
