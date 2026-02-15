from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from uom.db.async_repository import AsyncRepository
from uom.db.repository import User

_bearer = HTTPBearer(auto_error=False)


def get_repo(request: Request) -> AsyncRepository:
    """Dependency: gets the async repository instance attached to app state."""
    return request.app.state.repo  # type: ignore[no-any-return]


async def get_current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> User | None:
    """Auth dependency — returns User or None (when no users are configured)."""
    repo: AsyncRepository = get_repo(request)

    # 1. Check if ANY user exists (setup mode check)
    user_count = await repo.count_users()
    if user_count == 0:
        return None

    # 2. Extract token from Header, Cookie, or Query Param
    token = cred.credentials if cred else None
    if not token:
        token = request.cookies.get("uom_token")
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 3. Validate token
    user = await repo.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


def require_admin(user: User | None = Depends(get_current_user)) -> User | None:
    """Dependency: requires admin role (or no users configured)."""
    if user is None:
        return None  # open access
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user
