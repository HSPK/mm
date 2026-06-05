"""Typed library configuration stored in the active library database."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mm.config import get_config


class LibraryConfig(BaseModel):
    """Validated per-library configuration stored in the DB."""

    model_config = ConfigDict(extra="allow")

    library_id: str = ""  # Stable UUID4, generated once on first access
    library_name: str = ""
    import_template: str = Field(default_factory=lambda: get_config().import_.template)
    library_root: Path

    @field_validator("import_template")
    @classmethod
    def require_import_template(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("import_template cannot be empty")
        return value

    @field_validator("library_root")
    @classmethod
    def resolve_library_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()
