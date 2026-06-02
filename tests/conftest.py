"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from mm.db.sync_client import DBClient


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def db(tmp_path: Path) -> DBClient:
    """In-memory database client for tests."""
    db_path = tmp_path / "test.db"
    return DBClient(db_path)
