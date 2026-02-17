from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from uom.config import resolve_media_path
from uom.db.async_repository import AsyncRepository
from uom.db.dto import User

_bearer = HTTPBearer(auto_error=False)

# ── Token validation cache (avoids 2 DB queries per request) ──
# token → (User, expiry_ts)
_TOKEN_CACHE: dict[str, tuple[User, float]] = {}
_TOKEN_CACHE_TTL = 300  # 5 minutes
_TOKEN_CACHE_MAX = 256

# ── Media path cache (avoids DB query per thumbnail) ──
# media_id → (path_str, expiry_ts)
_MEDIA_PATH_CACHE: dict[int, tuple[str, float]] = {}
_MEDIA_PATH_TTL = 600  # 10 minutes
_MEDIA_PATH_MAX = 4096


def _evict_cache(cache: dict, max_size: int) -> None:
    """Remove oldest entries if cache exceeds max_size."""
    if len(cache) > max_size:
        # Remove oldest third
        to_remove = sorted(cache, key=lambda k: cache[k][-1])[: max_size // 3]
        for k in to_remove:
            cache.pop(k, None)


def invalidate_token_cache(token: str | None = None) -> None:
    """Invalidate a specific token or the entire cache."""
    if token:
        _TOKEN_CACHE.pop(token, None)
    else:
        _TOKEN_CACHE.clear()


def invalidate_media_path_cache(media_id: int | None = None) -> None:
    """Invalidate a specific media path or the entire cache."""
    if media_id:
        _MEDIA_PATH_CACHE.pop(media_id, None)
    else:
        _MEDIA_PATH_CACHE.clear()


def get_repo(request: Request) -> AsyncRepository:
    """Dependency: gets the async repository instance attached to app state."""
    return request.app.state.repo  # type: ignore[no-any-return]


def get_library_root(request: Request) -> str:
    """Return the library root directory (parent of the DB file)."""
    return request.app.state.library_root  # type: ignore[no-any-return]


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

    # 3. Check in-memory cache first
    now = time.monotonic()
    cached = _TOKEN_CACHE.get(token)
    if cached:
        user, expires = cached
        if now < expires:
            return user
        else:
            _TOKEN_CACHE.pop(token, None)

    # 4. Validate token via DB
    user = await repo.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 5. Store in cache
    _TOKEN_CACHE[token] = (user, now + _TOKEN_CACHE_TTL)
    _evict_cache(_TOKEN_CACHE, _TOKEN_CACHE_MAX)

    return user


def require_admin(user: User | None = Depends(get_current_user)) -> User | None:
    """Dependency: requires admin role (or no users configured)."""
    if user is None:
        return None  # open access
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user


async def get_media_path(request: Request, media_id: int) -> str:
    """Return the absolute file path for a media_id, using in-memory cache.

    Stored paths may be relative to the library root; this function resolves
    them so callers always receive an absolute path.
    """
    now = time.monotonic()
    cached = _MEDIA_PATH_CACHE.get(media_id)
    if cached:
        path, expires = cached
        if now < expires:
            return path
        else:
            _MEDIA_PATH_CACHE.pop(media_id, None)

    repo = get_repo(request)
    m = await repo.get_media_by_id(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    library_root = get_library_root(request)
    abs_path = resolve_media_path(m.path, library_root)

    _MEDIA_PATH_CACHE[media_id] = (abs_path, now + _MEDIA_PATH_TTL)
    _evict_cache(_MEDIA_PATH_CACHE, _MEDIA_PATH_MAX)
    return abs_path
