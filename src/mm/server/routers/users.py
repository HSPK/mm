from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from mm.db.dto import User
from mm.server.dependencies import get_db, require_admin
from mm.server.schemas import CreateUserBody, StatusOk, UserDetail, UserSummary

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserDetail])
async def list_users(
    request: Request,
    _admin: User | None = Depends(require_admin),
) -> list[UserDetail]:
    users = await get_db(request).user.list()
    return [
        UserDetail(
            id=u.id or 0,
            username=u.username,
            display_name=u.display_name or "",
            is_admin=bool(u.is_admin),
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.post("", response_model=UserSummary)
async def create_user(
    request: Request,
    body: CreateUserBody,
    _admin: User | None = Depends(require_admin),
) -> UserSummary:
    user = await get_db(request).user.create(
        body.username,
        body.password,
        body.display_name,
        body.is_admin,
    )
    return UserSummary(
        id=user.id or 0,
        username=user.username,
        display_name=user.display_name or "",
        is_admin=bool(user.is_admin),
    )


@router.delete("/{user_id}", response_model=StatusOk)
async def delete_user(
    request: Request,
    user_id: int,
    _admin: User | None = Depends(require_admin),
) -> StatusOk:
    await get_db(request).user.delete(user_id)
    return StatusOk()
