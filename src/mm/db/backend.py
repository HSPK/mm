"""Database backend parsing and URL construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

DatabaseBackend = Literal["sqlite", "postgres"]
_POSTGRES_SCHEMES = {"postgres", "postgresql"}


@dataclass(frozen=True)
class DatabaseTarget:
    """A database target that may be a SQLite path or PostgreSQL URL."""

    raw: str
    backend: DatabaseBackend
    manager_url: str
    display: str
    local_path: Path | None
    default_library_root: Path

    @classmethod
    def from_value(cls, value: str | Path) -> "DatabaseTarget":
        raw = str(value)
        parsed = urlparse(raw)
        if parsed.scheme in _POSTGRES_SCHEMES:
            return cls(
                raw=raw,
                backend="postgres",
                manager_url=raw,
                display=raw,
                local_path=None,
                default_library_root=Path.cwd().resolve(),
            )

        path = Path(raw).expanduser().resolve()
        return cls(
            raw=str(path),
            backend="sqlite",
            manager_url=f"aiosqlite:///{path}",
            display=str(path),
            local_path=path,
            default_library_root=path.parent,
        )

    @property
    def is_local_file(self) -> bool:
        return self.local_path is not None

    @property
    def identity(self) -> str:
        return self.display
