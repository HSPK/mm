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


# ── Section defaults & YAML override ──────────────────────────────────────────


def test_section_defaults_match_legacy_constants():
    cfg = CliConfig()

    assert cfg.paths.cache_dir == Path.home() / ".cache" / "mm"
    assert cfg.paths.thumbs_dir == cfg.paths.cache_dir / "thumbs"
    assert cfg.paths.geonames_dir == cfg.paths.cache_dir / "geonames"
    assert cfg.thumbnails.sizes == {
        "sm": (200, 200),
        "md": (400, 400),
        "lg": (800, 800),
        "xl": (1920, 1080),
    }
    assert cfg.thumbnails.http_cache_control == "public, max-age=31536000, immutable"
    assert cfg.clip.model_name == "ViT-B-32"
    assert cfg.clip.pretrained == "openai"
    assert cfg.clip.confidence_threshold == 0.25
    assert len(cfg.clip.labels) >= 35
    assert cfg.hashing.chunk_size == 8192
    assert cfg.import_.db_name == "mm.db"
    assert cfg.import_.template.startswith("{year}/")
    assert cfg.server.token_cache.ttl == 300
    assert cfg.server.token_cache.max == 256
    assert cfg.server.media_path_cache.ttl == 600
    assert cfg.server.media_path_cache.max == 4096


def test_yaml_override_round_trip(tmp_path: Path, monkeypatch):
    import yaml

    monkeypatch.setattr(app_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "mm.yaml")
    (tmp_path / "mm.yaml").write_text(
        yaml.safe_dump(
            {
                "paths": {"cache_dir": str(tmp_path / "cache")},
                "clip": {"model_name": "ViT-L-14", "confidence_threshold": 0.5},
                "hashing": {"chunk_size": 65536},
                "thumbnails": {"sizes": {"sm": [100, 100]}},
                "server": {"token_cache": {"ttl": 60, "max": 8}},
                "import": {"db_name": "library.db", "template": "{year}{ext}"},
            }
        )
    )
    app_config.reload_config()
    cfg = app_config.get_config()

    assert cfg.paths.cache_dir == tmp_path / "cache"
    assert cfg.paths.thumbs_dir == tmp_path / "cache" / "thumbs"
    assert cfg.clip.model_name == "ViT-L-14"
    assert cfg.clip.confidence_threshold == 0.5
    assert cfg.hashing.chunk_size == 65536
    assert cfg.thumbnails.sizes == {"sm": (100, 100)}
    assert cfg.server.token_cache.ttl == 60
    assert cfg.import_.db_name == "library.db"
    assert cfg.import_.template == "{year}{ext}"


def test_get_config_is_cached_and_reload_invalidates(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(app_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "mm.yaml")
    app_config.reload_config()

    first = app_config.get_config()
    assert app_config.get_config() is first  # same cached instance

    (tmp_path / "mm.yaml").write_text("clip:\n  model_name: foo\n")
    assert app_config.get_config() is first  # still cached

    app_config.reload_config()
    after = app_config.get_config()
    assert after is not first
    assert after.clip.model_name == "foo"
