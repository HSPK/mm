"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from mm.db.sync_repo import SyncRepo


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def repo(tmp_path: Path) -> SyncRepo:
    """In-memory repository for tests."""
    db_path = tmp_path / "test.db"
    return SyncRepo(db_path)
