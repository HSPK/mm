from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from uom.db.repository import User
from uom.server.dependencies import get_current_user, get_repo
from uom.server.schemas import ChangePasswordBody, LoginBody, SetupBody

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.get("/status")
async def auth_status(request: Request) -> dict[str, Any]:
    """Check if setup is needed or user is authenticated."""
    repo = get_repo(request)
    return {"setup_required": await repo.user_count() == 0}


@router.post("/setup")
async def auth_setup(request: Request, body: SetupBody) -> dict[str, Any]:
    """Create the first admin user. Only works when no users exist."""
    repo = get_repo(request)
    if await repo.user_count() > 0:
        raise HTTPException(400, "Setup already completed")
    user = await repo.create_user(
        body.username, password=body.password, display_name=body.display_name, is_admin=True
    )
    token = await repo.generate_token(user.id)  # type: ignore[arg-type]
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
        },
    }


@router.post("/login")
async def auth_login(request: Request, body: LoginBody) -> dict[str, Any]:
    repo = get_repo(request)
    user = await repo.verify_user(body.username, body.password)
    # user = repo.verify_user(body.username, body.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    token = await repo.generate_token(user.id)  # type: ignore[arg-type]
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
        },
    }


@router.post("/logout")
async def auth_logout(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> dict[str, str]:
    token = cred.credentials if cred else request.cookies.get("uom_token")
    if token:
        await get_repo(request).invalidate_token(token)
    return {"status": "ok"}


@router.get("/me")
async def auth_me(user: User | None = Depends(get_current_user)) -> dict[str, Any]:
    if user is None:
        return {"id": 0, "username": "admin", "display_name": "Admin", "is_admin": True}
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
    }


@router.post("/password")
async def auth_change_password(
    request: Request,
    body: ChangePasswordBody,
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    if user is None:
        raise HTTPException(400, "No users configured")
    repo = get_repo(request)
    if not await repo.verify_user(user.username, body.old_password):
        raise HTTPException(400, "Current password is incorrect")
    await repo.change_password(user.id, body.new_password)  # type: ignore[arg-type]
    return {"status": "ok"}
