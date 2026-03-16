"""SyncRepo — thin synchronous wrapper around AsyncRepository.

Used by CLI commands and core modules that cannot run in an async context.
Every async method on AsyncRepository is transparently bridged via a
persistent event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mm.db.async_repository import AsyncRepository


class SyncRepo:
    """Proxy that exposes every ``AsyncRepository`` method synchronously."""

    def __init__(self, db_path: str | Path) -> None:
        self._loop = asyncio.new_event_loop()
        self._repo = AsyncRepository(db_path)
        self._loop.run_until_complete(self._repo.connect())
        self._loop.run_until_complete(self._repo.init_db())

    # Forward attribute access: if the underlying attr is an async method,
    # return a sync wrapper; otherwise return it directly.
    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._repo, name)
        if asyncio.iscoroutinefunction(attr):

            def _sync_bridge(*args: Any, **kwargs: Any) -> Any:
                return self._loop.run_until_complete(attr(*args, **kwargs))

            _sync_bridge.__name__ = name
            _sync_bridge.__doc__ = getattr(attr, "__doc__", None)
            return _sync_bridge
        return attr

    def close(self) -> None:
        self._loop.close()
