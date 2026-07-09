from __future__ import annotations

from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, CliConfig, load_cli_config
from mm.organizer.filename import ParsedMediaFile
from mm.server.organizer_paths import is_relative_to
from mm.server.organizer_schemas import OrganizerItem


def source_kind_for_item(item: OrganizerItem) -> str:
    path = Path(item.path)
    configured_kind = configured_source_kind_for_path(path)
    if configured_kind:
        return configured_kind
    suffix = path.suffix.lower()
    media_type = item.media_type.lower()
    if suffix in AUDIO_EXTENSIONS:
        return "music"
    if suffix in VIDEO_EXTENSIONS:
        if media_type in {"tv", "episode", "season", "show", "series"}:
            return "tv"
        return "tv" if item.season is not None or item.episode is not None else "movies"
    return source_kind_for_media_type(media_type)


def source_kind(item: ParsedMediaFile) -> str:
    configured_kind = configured_source_kind_for_path(item.path)
    if configured_kind:
        return configured_kind
    media_type = item.media_type.lower()
    if item.is_audio:
        return "music"
    if item.is_video:
        if media_type in {"tv", "episode", "season", "show", "series"}:
            return "tv"
        return "tv" if item.season is not None or item.episode is not None else "movies"
    return source_kind_for_media_type(media_type)


def configured_roots_for_items(items: list[ParsedMediaFile], cfg: CliConfig) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for item in items:
        for source in cfg.organizer.media_sources.get(source_kind(item), []):
            path = str(Path(source).expanduser())
            if path not in seen:
                seen.add(path)
                roots.append(Path(path))
    return roots


def configured_source_kind_for_path(path: Path) -> str | None:
    cfg = load_cli_config()
    resolved = path.expanduser().resolve()
    matches: list[tuple[int, str]] = []
    for kind in ("movies", "tv", "music"):
        for source in cfg.organizer.media_sources.get(kind, []):
            root = Path(source).expanduser().resolve()
            if is_relative_to(resolved, root):
                matches.append((len(root.parts), kind))
    if not matches:
        return None
    matches.sort(reverse=True)
    if len(matches) > 1 and matches[0][0] == matches[1][0] and matches[0][1] != matches[1][1]:
        return None
    return matches[0][1]


def configured_root_for_path(path: Path) -> Path | None:
    cfg = load_cli_config()
    resolved = path.expanduser().resolve()
    matches: list[Path] = []
    for sources in cfg.organizer.media_sources.values():
        for source in sources:
            root = Path(source).expanduser().resolve()
            if is_relative_to(resolved, root):
                matches.append(root)
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item.parts), reverse=True)[0]


def source_kind_for_media_type(media_type: str) -> str:
    if media_type == "movie":
        return "movies"
    if media_type in {"tv", "episode", "season", "show", "series"}:
        return "tv"
    if media_type in {"album", "track", "music", "audio"}:
        return "music"
    return "music"
