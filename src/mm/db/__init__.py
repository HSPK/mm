"""Database package for media metadata, tags, and albums."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mm.db.client import AsyncDBClient
    from mm.db.dto import Media, Metadata, Tag, User
    from mm.db.sync_client import DBClient

__all__ = ["AsyncDBClient", "DBClient", "Media", "Metadata", "Tag", "User"]


def __getattr__(name: str) -> Any:
    if name == "AsyncDBClient":
        from mm.db.client import AsyncDBClient

        return AsyncDBClient
    if name == "DBClient":
        from mm.db.sync_client import DBClient

        return DBClient
    if name in {"Media", "Metadata", "Tag", "User"}:
        from mm.db import dto

        return getattr(dto, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
