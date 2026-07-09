from __future__ import annotations

from pathlib import Path

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.server.organizer_music_groups import music_album_key_from_path
from mm.server.organizer_scan import movie_entry_from_parsed, parse_configured_sources
from mm.server.organizer_schemas import OrganizerLibraryEntry, OrganizerLibraryResponse


async def organizer_library_groups(db: AsyncDBClient) -> OrganizerLibraryResponse:
    movies: list[OrganizerLibraryEntry] = []
    tv_groups: dict[str, list[ParsedMediaFile]] = {}
    music_groups: dict[str, list[ParsedMediaFile]] = {}
    cover_by_key: dict[str, int] = {}

    for media in await db.media.list():
        if media.deleted_at or media.id is None:
            continue
        parsed = parse_media_filename(Path(media.path))
        if not parsed:
            continue
        if parsed.media_type == "movie":
            movies.append(movie_entry_from_parsed(parsed, cover_id=media.id))
        elif parsed.media_type == "tv":
            key = f"tv:{parsed.title.lower()}"
            tv_groups.setdefault(key, []).append(parsed)
            cover_by_key.setdefault(key, media.id)
        elif parsed.media_type == "track":
            key = music_album_key_from_path(parsed.path)
            music_groups.setdefault(key, []).append(parsed)
            cover_by_key.setdefault(key, media.id)

    cfg = load_cli_config()
    for item in parse_configured_sources(
        cfg.organizer.media_sources.get("movies", []),
        recursive=True,
    ):
        if item.media_type == "movie":
            movies.append(movie_entry_from_parsed(item))
    for item in parse_configured_sources(
        cfg.organizer.media_sources.get("tv", []),
        recursive=True,
    ):
        if item.media_type == "tv":
            key = f"tv:{item.title.lower()}"
            tv_groups.setdefault(key, []).append(item)
    for item in parse_configured_sources(
        cfg.organizer.media_sources.get("music", []),
        recursive=True,
    ):
        if item.media_type == "track":
            key = music_album_key_from_path(item.path)
            music_groups.setdefault(key, []).append(item)

    return OrganizerLibraryResponse(
        movies=sorted(movies, key=lambda item: (item.title.lower(), item.year or 0)),
        tv=[
            OrganizerLibraryEntry(
                key=key,
                media_type="tv",
                title=items[0].title,
                subtitle=f"{len(items)} episode(s)",
                count=len(items),
                cover_id=cover_by_key.get(key),
                paths=[str(item.path) for item in items],
            )
            for key, items in sorted(tv_groups.items(), key=lambda item: item[1][0].title.lower())
        ],
        music=[
            OrganizerLibraryEntry(
                key=key,
                media_type="music",
                title=items[0].album or "Unknown Album",
                subtitle=items[0].artist or "Unknown Artist",
                count=len(items),
                cover_id=cover_by_key.get(key),
                artist=items[0].artist,
                album=items[0].album,
                paths=[str(item.path) for item in items],
            )
            for key, items in sorted(
                music_groups.items(),
                key=lambda item: (
                    (item[1][0].artist or "").lower(),
                    (item[1][0].album or "").lower(),
                ),
            )
        ],
    )
