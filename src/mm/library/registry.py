"""User-level library database registry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mm.config import (
    add_database,
    get_config,
    load_cli_config,
    remove_database,
    set_active_database,
)
from mm.db.backend import DatabaseTarget
from mm.io import local_storage


@dataclass(frozen=True)
class RegisteredDatabase:
    index: int
    name: str
    path: str
    backend: str
    active: bool
    exists: bool


@dataclass(frozen=True)
class DatabaseRegistration:
    index: int
    path: str


def list_registered_databases() -> list[RegisteredDatabase]:
    """Return configured databases with status metadata."""
    cfg = load_cli_config()
    return [_registered_database(i, entry, cfg.active) for i, entry in enumerate(cfg.databases)]


def _registered_database(entry_index, entry, active_index) -> RegisteredDatabase:  # noqa: ANN001
    target = DatabaseTarget.from_value(entry.path)
    return RegisteredDatabase(
        index=entry_index,
        name=entry.name,
        path=target.display,
        backend=target.backend,
        active=entry_index == active_index,
        exists=not target.is_local_file or local_storage.exists(target.local_path),
    )


def register_database(path: str | Path, name: str | None = None) -> DatabaseRegistration:
    """Register an existing DB file, directory, or PostgreSQL URL."""
    raw = str(path)
    target = DatabaseTarget.from_value(raw)
    if target.is_local_file:
        resolved = target.local_path
        assert resolved is not None
        if local_storage.is_dir(resolved):
            resolved = resolved / get_config().import_.db_name
        if not local_storage.exists(resolved):
            raise FileNotFoundError(resolved)
        target = DatabaseTarget.from_value(resolved)
    return DatabaseRegistration(index=add_database(target.display, name=name), path=target.display)


def activate_database(number: int) -> str:
    """Set active database by one-based user-facing number."""
    return set_active_database(number - 1)


def unregister_database(number: int) -> str:
    """Remove a database from the registry by one-based user-facing number."""
    return remove_database(number - 1)


def delete_database_file(path: str | Path) -> bool:
    """Delete a database file if it exists."""
    target = DatabaseTarget.from_value(path)
    if not target.is_local_file:
        return False
    assert target.local_path is not None
    if not local_storage.exists(target.local_path):
        return False
    local_storage.delete_file(target.local_path)
    return True
