from __future__ import annotations

from pathlib import Path

from mm.music.grouping import music_album_directory, music_album_key_from_path
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


def album_item_from_tracks(tracks: list[ParsedMediaFile]) -> ParsedMediaFile:
    first = tracks[0]
    album_directory = music_album_directory(first.path)
    return ParsedMediaFile(
        path=album_directory / first.path.name,
        media_type="album",
        title=first.album or first.title,
        artist=first.artist,
        album_artist=first.album_artist or first.artist,
        album=first.album,
        year=first.year,
        parse_template=first.parse_template,
        parse_relative_path=str(album_directory),
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
        album_artist=metadata.album_artist or metadata.artist or item.artist or "",
        album=metadata.title or metadata.album or item.album or "",
        year=metadata.year or item.year,
        overview=metadata.plot or "",
        genres=metadata.genres or [],
        styles=metadata.styles or [],
        tags=metadata.tags or [],
        composers=metadata.composers or [],
        external_ids=metadata.ids or {},
        title_variants=metadata.title_variants or {},
        artist_variants=metadata.artist_variants or {},
        album_artist_variants=metadata.album_artist_variants or metadata.artist_variants or {},
        album_variants=metadata.album_variants or metadata.title_variants or {},
        confidence=1,
    )
