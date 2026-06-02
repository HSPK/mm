"""Active library context helpers."""

from __future__ import annotations

from dataclasses import dataclass

from mm.config import get_active_db
from mm.db.backend import DatabaseTarget
from mm.db.sync_client import DBClient
from mm.library.settings import LibraryConfig


class NoActiveDatabaseError(RuntimeError):
    """Raised when no usable active database is configured."""


@dataclass
class ActiveLibrary:
    """Validated active library context."""

    database: str
    db: DBClient
    config: LibraryConfig

    def close(self) -> None:
        self.db.close()


def load_active_library() -> ActiveLibrary:
    """Open the active library and load its validated config."""
    database = get_active_db()
    if database is None:
        raise NoActiveDatabaseError
    target = DatabaseTarget.from_value(database)
    if target.is_local_file:
        from mm.io import local_storage

        assert target.local_path is not None
        if not local_storage.exists(target.local_path):
            raise NoActiveDatabaseError
    db = DBClient(database)
    return ActiveLibrary(database=target.display, db=db, config=db.library_config.get())
