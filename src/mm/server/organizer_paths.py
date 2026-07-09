from __future__ import annotations

from pathlib import Path

from mm.config import load_cli_config


def allowed_media_source_path(path: Path) -> bool:
    cfg = load_cli_config()
    roots = [
        Path(source).expanduser().resolve()
        for sources in cfg.organizer.media_sources.values()
        for source in sources
    ]
    return any(is_relative_to(path, root) for root in roots)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
