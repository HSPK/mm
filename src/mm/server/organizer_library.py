from __future__ import annotations

from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.server.organizer_schemas import OrganizerLibraryEntry, OrganizerLibraryResponse


async def organizer_library_groups(db: AsyncDBClient) -> OrganizerLibraryResponse:
    """Build library groups from the organizer projection only.

    This endpoint must be a query: filesystem discovery belongs to /scan or a
    sync job.  OrganizerMedia.path is unique, but the explicit set also keeps
    old imported rows from appearing twice during migration.
    """
    rows = await db.objects.fetchall(
        OrganizerMediaModel.select().where(OrganizerMediaModel.missing == 0)
    )
    by_path = {row.path: row for row in rows}
    movies: list[OrganizerLibraryEntry] = []
    tv: dict[str, list[OrganizerMediaModel]] = {}
    music: dict[str, list[OrganizerMediaModel]] = {}
    for row in by_path.values():
        if row.source_kind == "movies" or row.media_type == "movie":
            movies.append(
                OrganizerLibraryEntry(
                    key=f"movie:{row.item_uid or row.path}",
                    media_type="movie",
                    title=row.title,
                    subtitle=str(row.year or ""),
                    count=1,
                    cover_id=row.id,
                    year=row.year,
                    paths=[row.path],
                )
            )
        elif row.source_kind == "tv" or row.media_type == "tv":
            tv.setdefault(f"tv:{row.title.lower()}", []).append(row)
        elif row.source_kind == "music" or row.media_type == "track":
            key = f"music:{(row.artist or '').lower()}:{(row.album or row.title).lower()}"
            music.setdefault(key, []).append(row)

    return OrganizerLibraryResponse(
        movies=sorted(movies, key=lambda item: (item.title.lower(), item.year or 0)),
        tv=[
            OrganizerLibraryEntry(
                key=key,
                media_type="tv",
                title=group[0].title,
                subtitle=f"{len(group)} episode(s)",
                count=len(group),
                cover_id=group[0].id,
                paths=sorted(row.path for row in group),
            )
            for key, group in sorted(tv.items())
        ],
        music=[
            OrganizerLibraryEntry(
                key=key,
                media_type="music",
                title=group[0].album or "Unknown Album",
                subtitle=group[0].artist or "Unknown Artist",
                count=len(group),
                cover_id=group[0].id,
                artist=group[0].artist,
                album=group[0].album,
                paths=sorted(row.path for row in group),
            )
            for key, group in sorted(
                music.items(),
                key=lambda pair: (
                    (pair[1][0].artist or "").lower(),
                    (pair[1][0].album or "").lower(),
                ),
            )
        ],
    )
