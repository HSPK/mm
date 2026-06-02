from __future__ import annotations

from pathlib import Path

from mm import config as app_config
from mm.config import CliConfig, RegisteredDatabase


def test_app_config_defaults():
    cfg = CliConfig()

    assert cfg.databases == []
    assert cfg.active == -1
    assert cfg.active_database is None


def test_config_round_trip_and_database_helpers(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "mm.yaml"
    monkeypatch.setattr(app_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(app_config, "CONFIG_PATH", config_path)

    first = tmp_path / "first.db"
    second = tmp_path / "second.db"
    first.write_text("")
    second.write_text("")

    assert app_config.load_cli_config() == CliConfig()
    assert app_config.add_database(first, name="First") == 0
    assert app_config.add_database(second) == 1
    assert app_config.add_database(first) == 0
    assert app_config.get_active_db() == first.resolve()

    cfg = app_config.load_cli_config()
    assert cfg.databases == [
        RegisteredDatabase(path=first.resolve(), name="First"),
        RegisteredDatabase(path=second.resolve()),
    ]
    assert cfg.active_database == cfg.databases[0]

    assert app_config.set_active_database(1) == second.resolve()
    assert app_config.get_active_db() == second.resolve()

    assert app_config.remove_database(0) == first.resolve()
    cfg = app_config.load_cli_config()
    assert cfg.active == 0
    assert cfg.active_database == RegisteredDatabase(path=second.resolve())
