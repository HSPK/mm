"""Runtime helpers for starting the web server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mm.config import get_active_db
from mm.io import local_storage


@dataclass(frozen=True)
class ServerRuntime:
    db_path: Path
    library_dir: Path


def prepare_server_runtime() -> ServerRuntime | None:
    """Resolve active database and export it for the server app."""
    active = get_active_db()
    if not active or not local_storage.exists(active):
        return None

    os.environ["MM_DB"] = str(active)
    return ServerRuntime(db_path=active, library_dir=active.parent)
