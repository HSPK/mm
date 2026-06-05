"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from mm import config as app_config
from mm.db.sync_client import DBClient


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Drop the module-level config cache before every test."""
    app_config.reload_config()
    yield
    app_config.reload_config()


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def db(tmp_path: Path) -> DBClient:
    """In-memory database client for tests."""
    db_path = tmp_path / "test.db"
    return DBClient(db_path)
