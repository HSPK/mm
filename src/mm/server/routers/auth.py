from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db, invalidate_token_cache
from mm.server.schemas import (
    AuthStatus,
    ChangePasswordBody,
    LoginBody,
    LoginResponse,
    SetupBody,
    StatusMessage,
    UserSummary,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
    )


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request) -> AuthStatus:
    return AuthStatus(setup_required=await get_db(request).user.count() == 0)


@router.post("/setup", response_model=LoginResponse)
async def auth_setup(request: Request, body: SetupBody) -> LoginResponse:
    db = get_db(request)
    if await db.user.count() > 0:
        raise HTTPException(400, "Setup already completed")
    user = await db.user.create(
        body.username,
        password=body.password,
        display_name=body.display_name,
        is_admin=True,
    )
    token = await db.user.generate_token(user.id)  # type: ignore[arg-type]
    return LoginResponse(token=token, user=_user_summary(user))


@router.post("/login", response_model=LoginResponse)
async def auth_login(request: Request, body: LoginBody) -> LoginResponse:
    db = get_db(request)
    user = await db.user.verify(body.username, body.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    token = await db.user.generate_token(user.id)  # type: ignore[arg-type]
    return LoginResponse(token=token, user=_user_summary(user))


@router.post("/logout", response_model=StatusMessage)
async def auth_logout(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> StatusMessage:
    token = cred.credentials if cred else request.cookies.get("mm_token")
    if token:
        await get_db(request).user.invalidate(token)
        invalidate_token_cache(token)
    return StatusMessage(message="ok")


@router.get("/me", response_model=UserSummary)
async def auth_me(user: User | None = Depends(get_current_user)) -> UserSummary:
    if user is None:
        return UserSummary(id=0, username="admin", display_name="Admin", is_admin=True)
    return _user_summary(user)


@router.post("/password", response_model=StatusMessage)
async def auth_change_password(
    request: Request,
    body: ChangePasswordBody,
    user: User | None = Depends(get_current_user),
) -> StatusMessage:
    if user is None:
        raise HTTPException(400, "No users configured")
    db = get_db(request)
    if not await db.user.verify(user.username, body.old_password):
        raise HTTPException(400, "Current password is incorrect")
    await db.user.change_password(user.id, body.new_password)  # type: ignore[arg-type]
    return StatusMessage(message="ok")
