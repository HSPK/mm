from __future__ import annotations

import re
from pathlib import Path

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate
from mm.server.organizer_metadata import _read_metadata_file
from mm.server.organizer_schemas import OrganizerItem


def music_album_groups(items: list[OrganizerItem]) -> dict[str, list[OrganizerItem]]:
    groups: dict[str, list[OrganizerItem]] = {}
    for item in items:
        key = music_album_key_from_path(Path(item.path))
        groups.setdefault(key, []).append(item)
    return groups


def music_album_key_from_path(path: Path) -> str:
    directory = path.parent
    if disc_from_path_directory(directory.name) is not None:
        directory = directory.parent
    return f"music:{directory.expanduser().resolve()}"


def disc_from_path_directory(name: str) -> int | None:
    match = re.search(r"\bcd\s*(\d{1,3})\b", name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def album_item_from_tracks(tracks: list[ParsedMediaFile]) -> ParsedMediaFile:
    first = tracks[0]
    return ParsedMediaFile(
        path=first.path,
        media_type="album",
        title=first.album or first.title,
        artist=first.artist,
        album=first.album,
        year=first.year,
        parse_template=first.parse_template,
        parse_relative_path=str(first.path.parent),
        confidence=first.confidence,
    )


def album_metadata_exists(item: ParsedMediaFile) -> bool:
    return (item.path.parent / "album.nfo").is_file()


def candidate_from_album_nfo(item: ParsedMediaFile) -> ScrapeCandidate | None:
    metadata = _read_metadata_file(item.path.parent / "album.nfo")
    if not metadata.exists:
        return None
    return ScrapeCandidate(
        source="local",
        source_id=str(item.path.parent / "album.nfo"),
        media_type="album",
        title=metadata.title or item.album or item.title,
        artist=metadata.artist or item.artist or "",
        album=metadata.title or metadata.album or item.album or "",
        year=metadata.year or item.year,
        overview=metadata.plot or "",
        genres=metadata.genres or [],
        styles=metadata.styles or [],
        tags=metadata.tags or [],
        composers=metadata.composers or [],
        external_ids=metadata.ids or {},
        confidence=1,
    )
