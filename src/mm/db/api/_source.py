"""Shared source object for database API namespaces."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio


class DbSource:
    """Database source shared by API namespaces."""

    def __init__(self, objects: peewee_aio.Manager, db_path: Path) -> None:
        self.objects = objects
        self.db_path = db_path


class DbApi:
    """Base class for namespaced database APIs."""

    def __init__(self, source: DbSource) -> None:
        self.source = source

    @property
    def objects(self) -> peewee_aio.Manager:
        return self.source.objects
