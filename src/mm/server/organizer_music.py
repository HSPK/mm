from __future__ import annotations

from pathlib import Path

from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import first_artwork_path
from mm.server.organizer_schemas import OrganizerMusicAlbum, OrganizerMusicTrack


async def list_music_albums(db: AsyncDBClient) -> list[OrganizerMusicAlbum]:
    rows = await db.objects.fetchall(
        OrganizerMediaModel.select(
            OrganizerMediaModel.id,
            OrganizerMediaModel.path,
            OrganizerMediaModel.media_type,
            OrganizerMediaModel.title,
            OrganizerMediaModel.artist,
            OrganizerMediaModel.album,
            OrganizerMediaModel.year,
            OrganizerMediaModel.disc,
            OrganizerMediaModel.track,
            OrganizerMediaModel.has_metadata,
            OrganizerMediaModel.has_images,
            OrganizerMediaModel.has_lyrics,
        )
        .where(
            (OrganizerMediaModel.source_kind == "music")
            & (OrganizerMediaModel.media_type.in_(["track", "album"]))
            & (OrganizerMediaModel.missing == 0)
        )
        .order_by(OrganizerMediaModel.path)
    )

    grouped: dict[str, list[OrganizerMediaModel]] = {}
    for row in rows:
        grouped.setdefault(_album_key(Path(row.path)), []).append(row)

    albums = [_album_from_rows(key, rows) for key, rows in grouped.items() if rows]
    return sorted(albums, key=lambda album: (album.artist.lower(), album.title.lower()))


def _album_from_rows(key: str, rows: list[OrganizerMediaModel]) -> OrganizerMusicAlbum:
    sorted_rows = sorted(rows, key=_track_sort_key)
    first = sorted_rows[0]
    cover_path = first_artwork_path(Path(first.path), "track")
    tracks = [_track_from_row(row) for row in sorted_rows]
    return OrganizerMusicAlbum(
        key=key,
        title=first.album or first.title or "Unknown Album",
        artist=first.artist or "Unknown Artist",
        year=next((row.year for row in sorted_rows if row.year is not None), None),
        count=len(tracks),
        cover_path=str(cover_path) if cover_path else None,
        cover_playback_id=str(first.id) if first.id is not None else None,
        tracks=tracks,
    )


def _track_from_row(row: OrganizerMediaModel) -> OrganizerMusicTrack:
    return OrganizerMusicTrack(
        playback_id=str(row.id) if row.id is not None else None,
        path=row.path,
        title=row.title or Path(row.path).stem,
        artist=row.artist,
        album=row.album,
        year=row.year,
        disc=row.disc,
        track=row.track,
        metadata=bool(row.has_metadata),
        images=bool(row.has_images),
        lyrics=bool(row.has_lyrics),
    )


def _track_sort_key(row: OrganizerMediaModel) -> tuple[int, int, str]:
    return (
        row.disc or 1,
        row.track if row.track is not None else 9999,
        Path(row.path).name.lower(),
    )


def _album_key(path: Path) -> str:
    directory = path.parent
    if directory.name.lower().replace(" ", "").startswith("cd"):
        directory = directory.parent
    return str(directory.expanduser())
