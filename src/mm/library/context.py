"""Active library context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mm.config import get_active_db
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.library.settings import LibraryConfig


class NoActiveDatabaseError(RuntimeError):
    """Raised when no usable active database is configured."""


@dataclass
class ActiveLibrary:
    """Validated active library context."""

    db_path: Path
    db: DBClient
    config: LibraryConfig

    def close(self) -> None:
        self.db.close()


def load_active_library() -> ActiveLibrary:
    """Open the active library and load its validated config."""
    db_path = get_active_db()
    if db_path is None or not local_storage.exists(db_path):
        raise NoActiveDatabaseError
    db = DBClient(db_path)
    return ActiveLibrary(db_path=db_path, db=db, config=db.library_config.get())
