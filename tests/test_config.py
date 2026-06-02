from __future__ import annotations

from pathlib import Path

from mm import config as app_config
from mm.config import CliConfig, RegisteredDatabase
from mm.db.backend import DatabaseTarget


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
    assert app_config.get_active_db() == str(first.resolve())

    cfg = app_config.load_cli_config()
    assert cfg.databases == [
        RegisteredDatabase(path=str(first.resolve()), name="First"),
        RegisteredDatabase(path=str(second.resolve())),
    ]
    assert cfg.active_database == cfg.databases[0]

    assert app_config.set_active_database(1) == str(second.resolve())
    assert app_config.get_active_db() == str(second.resolve())

    assert app_config.remove_database(0) == str(first.resolve())
    cfg = app_config.load_cli_config()
    assert cfg.active == 0
    assert cfg.active_database == RegisteredDatabase(path=str(second.resolve()))


def test_postgres_database_target_and_config(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "mm.yaml"
    monkeypatch.setattr(app_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(app_config, "CONFIG_PATH", config_path)
    url = "postgresql://user:pass@example.com:5432/mm"

    target = DatabaseTarget.from_value(url)
    assert target.backend == "postgres"
    assert target.manager_url == url
    assert target.local_path is None

    assert app_config.add_database(url, name="Postgres") == 0
    assert app_config.get_active_db() == url
    assert app_config.load_cli_config().active_database == RegisteredDatabase(
        path=url,
        name="Postgres",
    )
