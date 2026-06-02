"""Runtime helpers for starting the web server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mm.config import get_active_db
from mm.db.backend import DatabaseTarget


@dataclass(frozen=True)
class ServerRuntime:
    database: str
    library_dir: Path


def prepare_server_runtime() -> ServerRuntime | None:
    """Resolve active database and export it for the server app."""
    active = get_active_db()
    if not active:
        return None
    target = DatabaseTarget.from_value(active)
    if target.is_local_file:
        from mm.io import local_storage

        assert target.local_path is not None
        if not local_storage.exists(target.local_path):
            return None

    os.environ["MM_DB"] = target.display
    return ServerRuntime(database=target.display, library_dir=target.default_library_root)
