from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Request
from uom.db.repository import User
from uom.server.dependencies import get_repo, require_admin
from uom.server.schemas import CreateUserBody

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("")
def list_users(
    request: Request,
    _admin: User | None = Depends(require_admin),
) -> list[dict[str, Any]]:
    repo = get_repo(request)
    return [
        {"id": u.id, "username": u.username, "display_name": u.display_name,
         "is_admin": u.is_admin,
         "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in repo.list_users()
    ]

@router.post("")
def create_user(
    request: Request,
    body: CreateUserBody,
    _admin: User | None = Depends(require_admin),
) -> dict[str, Any]:
    repo = get_repo(request)
    user = repo.create_user(
        body.username, body.password, body.display_name, body.is_admin,
    )
    return {"id": user.id, "username": user.username,
            "display_name": user.display_name, "is_admin": user.is_admin}

@router.delete("/{user_id}")
def delete_user(
    request: Request,
    user_id: int,
    _admin: User | None = Depends(require_admin),
) -> dict[str, str]:
    get_repo(request).delete_user(user_id)
    return {"status": "ok"}
