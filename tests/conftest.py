"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from uom.db.repository import Repository


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def repo(tmp_path: Path) -> Repository:
    """In-memory repository for tests."""
    db_path = tmp_path / "test.db"
    r = Repository(db_path)
    r.connect()
    r.init_db()
    return r
