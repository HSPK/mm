from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from mm import config as app_config
from mm.cli import cli
from mm.config import DEFAULT_DB_NAME, DEFAULT_IMPORT_TEMPLATE
from mm.library.setup import inspect_library_setup


def test_inspect_library_setup_does_not_require_library_name(tmp_path: Path):
    dest = tmp_path / "library"

    requirements = inspect_library_setup(dest)

    assert requirements.destination == dest.resolve()
    assert requirements.db_path == dest.resolve() / DEFAULT_DB_NAME
    assert requirements.needs_admin_user is True


def test_cli_init_creates_library_without_name_error(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setattr(app_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(app_config, "CONFIG_PATH", config_dir / "mm.yaml")
    dest = tmp_path / "library"

    result = CliRunner().invoke(
        cli,
        ["init", str(dest)],
        input=(f"My Library\n{DEFAULT_IMPORT_TEMPLATE}\n{dest}\nadmin\nsecret\nsecret\nn\n"),
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert (dest / DEFAULT_DB_NAME).exists()
    assert "Database ready" in result.output
    cfg = app_config.load_cli_config()
    assert cfg.active_database is not None
    assert cfg.active_database.name == "My Library"
    assert Path(cfg.active_database.path) == (dest / DEFAULT_DB_NAME).resolve()
