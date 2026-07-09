"""Filename template rendering for organized media layouts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

from mm.config import OrganizerTemplates
from mm.organizer.filename import ParsedMediaFile

_BAD_COMPONENT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTISPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class RenderedPath:
    relative_path: Path
    template: str


def render_media_path(item: ParsedMediaFile, templates: OrganizerTemplates) -> RenderedPath:
    template = {
        "movie": templates.movie,
        "tv": templates.tv,
        "track": templates.track,
        "album": templates.track,
    }.get(item.media_type)
    if template is None:
        raise ValueError(f"Unsupported media type: {item.media_type}")
    values = template_values(item)
    rendered = _format_template(template, values)
    parts = [_sanitize_component(part) for part in Path(rendered).parts if part not in {"", "."}]
    if not parts:
        raise ValueError(f"Template rendered an empty path for {item.path}")
    return RenderedPath(Path(*parts), template)


def template_values(item: ParsedMediaFile) -> dict[str, object]:
    year = item.year or ""
    artist = item.artist or "Unknown Artist"
    album = item.album or "Unknown Album"
    disc_folder = f"CD{item.disc}" if item.disc else ""
    return {
        "title": item.title,
        "show": item.title,
        "artist": artist,
        "album": album,
        "year": year,
        "season": item.season or 0,
        "episode": item.episode or 0,
        "episode_end": item.episode_end or "",
        "disc": item.disc or 0,
        "disc_folder": disc_folder,
        "track": item.track or 0,
        "ext": item.path.suffix,
        "stem": item.path.stem,
        "source_name": item.path.name,
    }


def _format_template(template: str, values: dict[str, object]) -> str:
    formatter = Formatter()
    rendered_parts: list[str] = []
    for literal, field_name, format_spec, conversion in formatter.parse(template):
        rendered_parts.append(literal)
        if field_name is None:
            continue
        value = values.get(field_name, "")
        if value == "" and format_spec:
            rendered_parts.append("")
            continue
        rendered_parts.append(format(value, format_spec) if format_spec else str(value))
        if conversion:
            raise ValueError(f"Unsupported conversion in template field: {field_name!r}")
    return "".join(rendered_parts)


def _sanitize_component(value: str) -> str:
    text = _BAD_COMPONENT_CHARS.sub(" ", value)
    text = _MULTISPACE.sub(" ", text).strip(" .")
    return text or "_"
