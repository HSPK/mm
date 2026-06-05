from __future__ import annotations

import time
from pathlib import Path

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.library.settings import LibraryConfig
from mm.media.thumbnails import cache_dir_for_library
from mm.utils.paths import resolve_media_path

_bearer = HTTPBearer(auto_error=False)

# Token cache: token → (User, expiry_ts)
_TOKEN_CACHE: dict[str, tuple[User, float]] = {}
_TOKEN_CACHE_TTL = 300
_TOKEN_CACHE_MAX = 256

# Media path cache: media_id → (path_str, expiry_ts)
_MEDIA_PATH_CACHE: dict[int, tuple[str, float]] = {}
_MEDIA_PATH_TTL = 600
_MEDIA_PATH_MAX = 4096


def _evict_cache(cache: dict, max_size: int) -> None:
    if len(cache) > max_size:
        to_remove = sorted(cache, key=lambda k: cache[k][-1])[: max_size // 3]
        for k in to_remove:
            cache.pop(k, None)


def invalidate_token_cache(token: str | None = None) -> None:
    if token:
        _TOKEN_CACHE.pop(token, None)
    else:
        _TOKEN_CACHE.clear()


def invalidate_media_path_cache(media_id: int | None = None) -> None:
    if media_id:
        _MEDIA_PATH_CACHE.pop(media_id, None)
    else:
        _MEDIA_PATH_CACHE.clear()


def get_db(request: Request) -> AsyncDBClient:
    return request.app.state.db  # type: ignore[no-any-return]


def get_library_config(request: Request) -> LibraryConfig:
    return request.app.state.config  # type: ignore[no-any-return]


def get_thumb_cache_dir(request: Request) -> Path:
    """Per-library thumbnail cache dir, namespaced by ``library_id``."""
    config: LibraryConfig | None = getattr(request.app.state, "config", None)
    library_id = config.library_id if config else None
    return cache_dir_for_library(library_id)


async def get_current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> User | None:
    """Returns User, or None when no users are configured (open access)."""
    db: AsyncDBClient = get_db(request)

    user_count = await db.user.count()
    if user_count == 0:
        return None

    token = cred.credentials if cred else None
    if not token:
        token = request.cookies.get("mm_token")
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    now = time.monotonic()
    cached = _TOKEN_CACHE.get(token)
    if cached:
        user, expires = cached
        if now < expires:
            return user
        else:
            _TOKEN_CACHE.pop(token, None)

    user = await db.user.get_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    _TOKEN_CACHE[token] = (user, now + _TOKEN_CACHE_TTL)
    _evict_cache(_TOKEN_CACHE, _TOKEN_CACHE_MAX)

    return user


def require_admin(user: User | None = Depends(get_current_user)) -> User | None:
    if user is None:
        return None
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user


async def get_media_path(request: Request, media_id: int) -> str:
    """Return the absolute file path for a media_id (cached)."""
    now = time.monotonic()
    cached = _MEDIA_PATH_CACHE.get(media_id)
    if cached:
        path, expires = cached
        if now < expires:
            return path
        else:
            _MEDIA_PATH_CACHE.pop(media_id, None)

    db = get_db(request)
    m = await db.media.get(media_id)
    if not m:
        raise HTTPException(404, "Media not found")

    config = get_library_config(request)
    abs_path = resolve_media_path(m.path, config.library_root)

    _MEDIA_PATH_CACHE[media_id] = (abs_path, now + _MEDIA_PATH_TTL)
    _evict_cache(_MEDIA_PATH_CACHE, _MEDIA_PATH_MAX)
    return abs_path
