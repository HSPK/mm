"""User-level library database registry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mm.config import (
    DEFAULT_DB_NAME,
    add_database,
    load_cli_config,
    remove_database,
    set_active_database,
)
from mm.io import local_storage


@dataclass(frozen=True)
class RegisteredDatabase:
    index: int
    name: str
    path: Path
    active: bool
    exists: bool


@dataclass(frozen=True)
class DatabaseRegistration:
    index: int
    path: Path


def list_registered_databases() -> list[RegisteredDatabase]:
    """Return configured databases with status metadata."""
    cfg = load_cli_config()
    return [
        RegisteredDatabase(
            index=i,
            name=entry.name,
            path=entry.path,
            active=i == cfg.active,
            exists=local_storage.exists(entry.path),
        )
        for i, entry in enumerate(cfg.databases)
    ]


def register_database(path: Path, name: str | None = None) -> DatabaseRegistration:
    """Register an existing DB file or directory containing the default DB."""
    resolved = path.resolve()
    if local_storage.is_dir(resolved):
        resolved = resolved / DEFAULT_DB_NAME
    if not local_storage.exists(resolved):
        raise FileNotFoundError(resolved)
    return DatabaseRegistration(index=add_database(resolved, name=name), path=resolved)


def activate_database(number: int) -> Path:
    """Set active database by one-based user-facing number."""
    return set_active_database(number - 1)


def unregister_database(number: int) -> Path:
    """Remove a database from the registry by one-based user-facing number."""
    return remove_database(number - 1)


def delete_database_file(path: Path) -> bool:
    """Delete a database file if it exists."""
    if not local_storage.exists(path):
        return False
    local_storage.delete_file(path)
    return True
