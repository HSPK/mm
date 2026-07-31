from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, CliConfig, load_cli_config
from mm.organizer.filename import ParsedMediaFile
from mm.server.organizer_paths import is_relative_to
from mm.server.organizer_schemas import OrganizerItem


@dataclass(frozen=True)
class ResolvedOrganizerSource:
    kind: str
    root: Path | None


@dataclass(frozen=True)
class ConfiguredOrganizerSource:
    kind: str
    match_root: Path
    root: Path


@dataclass(frozen=True)
class OrganizerSourceResolver:
    sources: tuple[ConfiguredOrganizerSource, ...]

    @classmethod
    def from_config(cls, cfg: CliConfig | None = None) -> OrganizerSourceResolver:
        config = cfg or load_cli_config()
        sources = [
            ConfiguredOrganizerSource(
                kind=kind,
                match_root=_normalized_path(Path(source)),
                root=Path(source).expanduser().resolve(),
            )
            for kind in ("movies", "tv", "music")
            for source in config.organizer.media_sources.get(kind, [])
        ]
        sources.sort(key=lambda source: len(source.match_root.parts), reverse=True)
        return cls(sources=tuple(sources))

    def resolve_item(self, item: OrganizerItem) -> ResolvedOrganizerSource:
        path = Path(item.path)
        configured_kind, root = self._configured_source(path)
        return ResolvedOrganizerSource(
            kind=configured_kind or _fallback_item_kind(item, path),
            root=root,
        )

    def resolve_parsed(self, item: ParsedMediaFile) -> ResolvedOrganizerSource:
        configured_kind, root = self._configured_source(item.path)
        return ResolvedOrganizerSource(
            kind=configured_kind or _fallback_parsed_kind(item),
            root=root,
        )

    def configured_kind_for_path(self, path: Path) -> str | None:
        return self._configured_source(path)[0]

    def configured_root_for_path(self, path: Path) -> Path | None:
        return self._configured_source(path)[1]

    def _configured_source(self, path: Path) -> tuple[str | None, Path | None]:
        normalized = _normalized_path(path)
        matches: list[tuple[int, ConfiguredOrganizerSource]] = []
        for source in self.sources:
            if is_relative_to(normalized, source.match_root):
                matches.append((len(source.match_root.parts), source))
            elif source.root != source.match_root and is_relative_to(normalized, source.root):
                matches.append((len(source.root.parts), source))
        if not matches:
            return None, None
        best_depth = max(depth for depth, _source in matches)
        nearest = [source for depth, source in matches if depth == best_depth]
        kinds = {source.kind for source in nearest}
        return (next(iter(kinds)) if len(kinds) == 1 else None), nearest[0].root


def _normalized_path(path: Path) -> Path:
    return Path(os.path.normcase(os.path.abspath(path.expanduser())))


def source_kind_for_item(
    item: OrganizerItem,
    resolver: OrganizerSourceResolver | None = None,
) -> str:
    return (resolver or OrganizerSourceResolver.from_config()).resolve_item(item).kind


def _fallback_item_kind(item: OrganizerItem, path: Path) -> str:
    suffix = path.suffix.lower()
    media_type = item.media_type.lower()
    if suffix in AUDIO_EXTENSIONS:
        return "music"
    if suffix in VIDEO_EXTENSIONS:
        if media_type in {"tv", "episode", "season", "show", "series"}:
            return "tv"
        return "tv" if item.season is not None or item.episode is not None else "movies"
    return source_kind_for_media_type(media_type)


def source_kind(
    item: ParsedMediaFile,
    resolver: OrganizerSourceResolver | None = None,
) -> str:
    return (resolver or OrganizerSourceResolver.from_config()).resolve_parsed(item).kind


def _fallback_parsed_kind(item: ParsedMediaFile) -> str:
    media_type = item.media_type.lower()
    if item.is_audio:
        return "music"
    if item.is_video:
        if media_type in {"tv", "episode", "season", "show", "series"}:
            return "tv"
        return "tv" if item.season is not None or item.episode is not None else "movies"
    return source_kind_for_media_type(media_type)


def configured_roots_for_items(items: list[ParsedMediaFile], cfg: CliConfig) -> list[Path]:
    resolver = OrganizerSourceResolver.from_config(cfg)
    kinds = {resolver.resolve_parsed(item).kind for item in items}
    return list(dict.fromkeys(source.root for source in resolver.sources if source.kind in kinds))


def configured_source_kind_for_path(
    path: Path,
    resolver: OrganizerSourceResolver | None = None,
) -> str | None:
    return (resolver or OrganizerSourceResolver.from_config()).configured_kind_for_path(path)


def configured_root_for_path(
    path: Path,
    resolver: OrganizerSourceResolver | None = None,
) -> Path | None:
    return (resolver or OrganizerSourceResolver.from_config()).configured_root_for_path(path)


def source_kind_for_media_type(media_type: str) -> str:
    if media_type == "movie":
        return "movies"
    if media_type in {"tv", "episode", "season", "show", "series"}:
        return "tv"
    if media_type in {"album", "track", "music", "audio"}:
        return "music"
    return "music"
