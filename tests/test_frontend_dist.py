from pathlib import Path

from mm.server.app import resolve_web_dist


def test_source_checkout_prefers_fresh_web_dist(tmp_path: Path):
    module_file = tmp_path / "repo" / "src" / "mm" / "server" / "app.py"
    source_dist = tmp_path / "repo" / "web" / "dist"
    embedded = tmp_path / "repo" / "src" / "mm" / "_web_dist"
    source_dist.mkdir(parents=True)
    embedded.mkdir(parents=True)

    assert resolve_web_dist(module_file=module_file, env={}) == source_dist


def test_configured_web_dist_has_highest_priority(tmp_path: Path):
    module_file = tmp_path / "repo" / "src" / "mm" / "server" / "app.py"
    configured = tmp_path / "configured-dist"
    configured.mkdir()

    assert (
        resolve_web_dist(
            module_file=module_file,
            env={"MM_WEB_DIST": str(configured)},
        )
        == configured
    )
