from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.music.grouping import music_album_key_from_path
from mm.organizer.artwork_cache import first_artwork_path
from mm.organizer.localization import (
    canonicalize_music_artist,
    is_known_chinese_artist,
    select_localized_name,
)
from mm.server.music_schemas import (
    MusicAlbum,
    MusicAlbumsResponse,
    MusicArtist,
    MusicArtistsResponse,
    MusicTrack,
    MusicTracksResponse,
)
from mm.server.organizer_schemas import OrganizerItem
from mm.server.utils import content_type_for


@dataclass(frozen=True)
class _MusicCatalog:
    language: str
    rows: list[OrganizerMediaModel]
    tracks_by_album: dict[str, list[OrganizerMediaModel]]
    tracks_by_artist: dict[str, list[OrganizerMediaModel]]
    search_text: dict[int, str]
    album_search_text: dict[str, str]
    albums: list[MusicAlbum]
    artists: list[MusicArtist]


_MUSIC_CATALOG_CACHE: dict[str, tuple[int, float, _MusicCatalog]] = {}
_MUSIC_ROWS_LOCKS: dict[str, asyncio.Lock] = {}
_MUSIC_CATALOG_EPOCH: dict[str, int] = {}
_MUSIC_ROWS_CACHE_SECONDS = 30.0


def _opaque_id(prefix: str, value: str) -> str:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=16).hexdigest()
    return f"{prefix}_{digest}"


def album_id_for_path(path: Path) -> str:
    return _opaque_id("album", music_album_key_from_path(path))


def artist_id_for_name(name: str | None) -> str:
    return _opaque_id("artist", (name or "Unknown Artist").casefold())


def track_id_for_item(
    item: OrganizerItem,
    *,
    existing_id: str | None = None,
    item_uid: str | None = None,
) -> str:
    return (
        _external_id(
            "track",
            item.metadata_ids,
            (
                "musicbrainz_recording",
                "isrc",
                "netease_track",
                "qqmusic_track",
                "itunes_track",
            ),
        )
        or existing_id
        or _opaque_id("track", item_uid or item.item_uid or item.path)
    )


def album_id_for_item(
    item: OrganizerItem,
    *,
    existing_id: str | None = None,
) -> str:
    return (
        _external_id(
            "album",
            item.metadata_ids,
            (
                "musicbrainz_release_group",
                "musicbrainz_release",
                "barcode",
                "netease_album",
                "qqmusic_album",
                "itunes_album",
            ),
        )
        or existing_id
        or album_id_for_path(Path(item.path))
    )


def artist_id_for_item(
    item: OrganizerItem,
    *,
    existing_id: str | None = None,
) -> str:
    variants = {
        value.casefold() for value in item.metadata_artist_variants.values() if value.strip()
    }
    fallback = "|".join(sorted(variants)) or (item.artist or "Unknown Artist").casefold()
    if internal_artist := item.metadata_ids.get("mm_artist"):
        canonical = canonicalize_music_artist(internal_artist) or internal_artist
        return artist_id_for_name(canonical.casefold())
    return (
        _external_id(
            "artist",
            item.metadata_ids,
            (
                "mm_artist",
                "musicbrainz_artist_credit",
                "musicbrainz_artist",
                "netease_artist_credit",
                "netease_artist",
                "qqmusic_artist_credit",
                "qqmusic_artist",
                "itunes_artist",
            ),
        )
        or existing_id
        or artist_id_for_name(fallback)
    )


def album_artist_id_for_item(
    item: OrganizerItem,
    *,
    existing_id: str | None = None,
) -> str:
    variants = {
        value.casefold() for value in item.metadata_album_artist_variants.values() if value.strip()
    }
    fallback_name = item.album_artist or item.artist or "Unknown Artist"
    fallback = "|".join(sorted(variants)) or fallback_name.casefold()
    if is_known_chinese_artist(fallback_name):
        canonical = canonicalize_music_artist(fallback_name) or fallback_name
        return artist_id_for_name(canonical.casefold())
    if internal_artist := item.metadata_ids.get("mm_album_artist"):
        canonical = canonicalize_music_artist(internal_artist) or internal_artist
        return artist_id_for_name(canonical.casefold())
    for source_key, canonical_key in (
        ("musicbrainz_album_artist_credit", "musicbrainz_artist_credit"),
        ("netease_album_artist_credit", "netease_artist_credit"),
        ("qqmusic_album_artist_credit", "qqmusic_artist_credit"),
        ("itunes_album_artist", "itunes_artist"),
    ):
        if value := item.metadata_ids.get(source_key):
            return _opaque_id("artist", f"{canonical_key}:{value}")
    return (
        _external_id(
            "artist",
            item.metadata_ids,
            (
                "musicbrainz_artist_credit",
                "musicbrainz_artist",
                "netease_artist",
                "qqmusic_artist",
                "itunes_artist",
            ),
        )
        or existing_id
        or artist_id_for_name(fallback)
    )


def _external_id(
    prefix: str,
    external_ids: dict[str, str],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = external_ids.get(key)
        if value:
            return _opaque_id(prefix, f"{key}:{value}")
    return None


def album_id_for_row(row: OrganizerMediaModel) -> str:
    return row.music_album_id or album_id_for_path(Path(row.path))


def artist_id_for_row(row: OrganizerMediaModel) -> str:
    return row.music_artist_id or artist_id_for_name(row.artist)


def track_id_for_row(row: OrganizerMediaModel) -> str:
    return row.music_track_id or _opaque_id("track", row.path)


def album_artist_id_for_row(row: OrganizerMediaModel) -> str:
    return row.music_album_artist_id or artist_id_for_row(row)


async def list_music_albums(
    db: AsyncDBClient,
    *,
    offset: int = 0,
    limit: int = 50,
    query: str = "",
    artist_id: str = "",
) -> MusicAlbumsResponse:
    catalog = await _music_catalog(db)
    albums = catalog.albums
    if artist_id:
        albums = [
            album
            for album in albums
            if any(
                artist_id_for_row(row) == artist_id
                for row in catalog.tracks_by_album.get(album.album_id, [])
            )
        ]
    if query:
        needle = query.casefold()
        albums = [
            album for album in albums if needle in catalog.album_search_text.get(album.album_id, "")
        ]
    total = len(albums)
    return MusicAlbumsResponse(
        albums=albums[offset : offset + limit],
        offset=offset,
        limit=limit,
        total=total,
    )


async def get_music_album(
    db: AsyncDBClient,
    album_id: str,
) -> MusicAlbum | None:
    catalog = await _music_catalog(db)
    return next((album for album in catalog.albums if album.album_id == album_id), None)


async def list_music_tracks(
    db: AsyncDBClient,
    *,
    offset: int = 0,
    limit: int = 100,
    query: str = "",
    album_id: str = "",
    artist_id: str = "",
) -> MusicTracksResponse:
    catalog = await _music_catalog(db)
    rows = catalog.rows
    if album_id:
        rows = catalog.tracks_by_album.get(album_id, [])
    elif artist_id:
        rows = catalog.tracks_by_artist.get(artist_id, [])
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in catalog.search_text.get(int(row.id), "")]
    return MusicTracksResponse(
        tracks=[_track_from_row(row, catalog.language) for row in rows[offset : offset + limit]],
        offset=offset,
        limit=limit,
        total=len(rows),
    )


async def list_music_artists(
    db: AsyncDBClient,
    *,
    offset: int = 0,
    limit: int = 100,
    query: str = "",
) -> MusicArtistsResponse:
    result = (await _music_catalog(db)).artists
    if query:
        result = [artist for artist in result if query.casefold() in artist.name.casefold()]
    return MusicArtistsResponse(
        artists=result[offset : offset + limit],
        offset=offset,
        limit=limit,
        total=len(result),
    )


async def get_music_artist(
    db: AsyncDBClient,
    artist_id: str,
) -> MusicArtist | None:
    catalog = await _music_catalog(db)
    return next((artist for artist in catalog.artists if artist.artist_id == artist_id), None)


async def _music_catalog(db: AsyncDBClient) -> _MusicCatalog:
    from mm.config import load_cli_config

    language = load_cli_config().scrapers.language
    key = f"{db.database}|{language}"
    epoch = _MUSIC_CATALOG_EPOCH.get(key, 0)
    cached = _MUSIC_CATALOG_CACHE.get(key)
    if cached and cached[0] == epoch and time.monotonic() - cached[1] < _MUSIC_ROWS_CACHE_SECONDS:
        return cached[2]
    lock = _MUSIC_ROWS_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        epoch = _MUSIC_CATALOG_EPOCH.get(key, 0)
        cached = _MUSIC_CATALOG_CACHE.get(key)
        if (
            cached
            and cached[0] == epoch
            and time.monotonic() - cached[1] < _MUSIC_ROWS_CACHE_SECONDS
        ):
            return cached[2]
        rows = await db.objects.fetchall(
            OrganizerMediaModel.select(
                OrganizerMediaModel.id,
                OrganizerMediaModel.path,
                OrganizerMediaModel.title,
                OrganizerMediaModel.artist,
                OrganizerMediaModel.album_artist,
                OrganizerMediaModel.album,
                OrganizerMediaModel.year,
                OrganizerMediaModel.disc,
                OrganizerMediaModel.track,
                OrganizerMediaModel.has_metadata,
                OrganizerMediaModel.has_images,
                OrganizerMediaModel.has_lyrics,
                OrganizerMediaModel.audio_duration,
                OrganizerMediaModel.audio_mime_type,
                OrganizerMediaModel.music_track_id,
                OrganizerMediaModel.music_album_id,
                OrganizerMediaModel.music_artist_id,
                OrganizerMediaModel.music_album_artist_id,
                OrganizerMediaModel.music_title_variants,
                OrganizerMediaModel.music_artist_variants,
                OrganizerMediaModel.music_album_artist_variants,
                OrganizerMediaModel.music_album_variants,
            )
            .where(
                (OrganizerMediaModel.source_kind == "music")
                & (OrganizerMediaModel.media_type == "track")
                & (OrganizerMediaModel.missing == 0)
            )
            .order_by(OrganizerMediaModel.path)
        )
        catalog = await asyncio.to_thread(_build_music_catalog, rows, language)
        if epoch == _MUSIC_CATALOG_EPOCH.get(key, 0):
            _MUSIC_CATALOG_CACHE[key] = (epoch, time.monotonic(), catalog)
        while len(_MUSIC_CATALOG_CACHE) > 2:
            evicted = next(iter(_MUSIC_CATALOG_CACHE))
            _MUSIC_CATALOG_CACHE.pop(evicted)
            evicted_lock = _MUSIC_ROWS_LOCKS.get(evicted)
            if evicted_lock is not None and not evicted_lock.locked():
                _MUSIC_ROWS_LOCKS.pop(evicted, None)
        return catalog


def invalidate_music_catalog(database: str | None = None) -> None:
    if database is None:
        _MUSIC_CATALOG_CACHE.clear()
        for key in tuple(_MUSIC_ROWS_LOCKS):
            _MUSIC_CATALOG_EPOCH[key] = _MUSIC_CATALOG_EPOCH.get(key, 0) + 1
        return
    prefix = f"{database}|"
    for key in {
        *[item for item in _MUSIC_CATALOG_CACHE if item.startswith(prefix)],
        *[item for item in _MUSIC_ROWS_LOCKS if item.startswith(prefix)],
    }:
        _MUSIC_CATALOG_EPOCH[key] = _MUSIC_CATALOG_EPOCH.get(key, 0) + 1
        _MUSIC_CATALOG_CACHE.pop(key, None)


def _album_groups(rows: list[OrganizerMediaModel]) -> dict[str, list[OrganizerMediaModel]]:
    groups: dict[str, list[OrganizerMediaModel]] = {}
    for row in rows:
        groups.setdefault(album_id_for_row(row), []).append(row)
    return groups


def _build_music_catalog(
    rows: list[OrganizerMediaModel],
    language: str = "",
) -> _MusicCatalog:
    _merge_canonical_track_variants(rows)
    _merge_canonical_album_variants(rows)
    rows.sort(
        key=lambda row: (
            _localized_artist(row, language).casefold(),
            _localized_album(row, language).casefold(),
            *_track_sort_key(row),
        )
    )
    groups = _album_groups(rows)
    albums = [_album_from_rows(group, language) for group in groups.values() if group]
    albums.sort(key=lambda album: (album.artist.casefold(), album.title.casefold(), album.album_id))
    tracks_by_album = {album_id_for_row(group[0]): group for group in groups.values() if group}
    tracks_by_artist: dict[str, list[OrganizerMediaModel]] = {}
    search_text: dict[int, str] = {}
    album_search_text: dict[str, str] = {}
    for row in rows:
        if row.id is not None:
            search_text[int(row.id)] = " ".join(
                (
                    row.title or "",
                    row.artist or "",
                    row.album or "",
                    *_variant_values(row.music_title_variants),
                    *_variant_values(row.music_artist_variants),
                    *_variant_values(row.music_album_variants),
                )
            ).casefold()
    for row in rows:
        tracks_by_artist.setdefault(artist_id_for_row(row), []).append(row)
    for album in albums:
        album_rows = tracks_by_album.get(album.album_id, [])
        album_search_text[album.album_id] = " ".join(
            [
                album.title,
                album.artist,
                *(search_text.get(int(row.id), "") for row in album_rows if row.id is not None),
            ]
        ).casefold()
    return _MusicCatalog(
        language=language,
        rows=rows,
        tracks_by_album=tracks_by_album,
        tracks_by_artist=tracks_by_artist,
        search_text=search_text,
        album_search_text=album_search_text,
        albums=albums,
        artists=_artists_from_rows(rows, language),
    )


def _artists_from_rows(
    rows: list[OrganizerMediaModel],
    language: str = "",
) -> list[MusicArtist]:
    artists: dict[str, MusicArtist] = {}
    grouped: dict[str, list[OrganizerMediaModel]] = {}
    for row in rows:
        grouped.setdefault(artist_id_for_row(row), []).append(row)
    for artist_id, artist_rows in grouped.items():
        first = artist_rows[0]
        name = _localized_artist(first, language)
        variants = _merged_variants(artist_rows, "music_artist_variants")
        name = select_localized_name(variants, language, name)
        cover_path = first_artwork_path(Path(first.path), "track")
        artists[artist_id] = MusicArtist(
            artist_id=artist_id,
            name=name,
            album_count=len({album_id_for_row(row) for row in artist_rows}),
            track_count=len(artist_rows),
            cover_playback_id=str(first.id) if cover_path and first.id is not None else None,
            name_variants=variants,
        )
    for album_rows in _album_groups(rows).values():
        first = album_rows[0]
        artist_id = album_artist_id_for_row(first)
        if artist_id in artists:
            continue
        variants = _merged_variants(
            album_rows,
            "music_album_artist_variants",
        )
        name = select_localized_name(
            variants,
            language,
            _localized_album_artist(first, language),
        )
        cover_path = first_artwork_path(Path(first.path), "track")
        artists[artist_id] = MusicArtist(
            artist_id=artist_id,
            name=name,
            album_count=1,
            track_count=len(album_rows),
            cover_playback_id=str(first.id) if cover_path and first.id is not None else None,
            name_variants=variants,
        )
    return sorted(
        artists.values(),
        key=lambda artist: (artist.name.casefold(), artist.artist_id),
    )


def _album_from_rows(rows: list[OrganizerMediaModel], language: str = "") -> MusicAlbum:
    sorted_rows = sorted(rows, key=_track_sort_key)
    first = sorted_rows[0]
    cover_path = first_artwork_path(Path(first.path), "track")
    title_variants = _merged_variants(sorted_rows, "music_album_variants")
    artist_id = album_artist_id_for_row(first)
    artist_rows = [row for row in sorted_rows if album_artist_id_for_row(row) == artist_id]
    artist_variants = _merged_variants(
        artist_rows,
        "music_album_artist_variants",
    ) or _merged_variants(artist_rows, "music_artist_variants")
    title = select_localized_name(
        title_variants,
        language,
        _localized_album(first, language),
    )
    artist = select_localized_name(
        artist_variants,
        language,
        _localized_album_artist(first, language),
    )
    return MusicAlbum(
        album_id=album_id_for_row(first),
        artist_id=artist_id,
        album_artist_id=artist_id,
        key=album_id_for_row(first),
        title=title,
        artist=artist,
        year=next((row.year for row in sorted_rows if row.year is not None), None),
        count=len(sorted_rows),
        cover_playback_id=str(first.id) if cover_path and first.id is not None else None,
        title_variants=title_variants,
        artist_variants=artist_variants,
    )


def _track_from_row(row: OrganizerMediaModel, language: str = "") -> MusicTrack:
    title_variants = _variant_map(row.music_title_variants)
    artist_variants = _variant_map(row.music_artist_variants)
    album_variants = _variant_map(row.music_album_variants)
    return MusicTrack(
        track_id=track_id_for_row(row),
        playback_id=str(row.id) if row.id is not None else None,
        title=_localized_title(row, language),
        artist=_localized_artist(row, language),
        album=_localized_album(row, language),
        year=row.year,
        disc=row.disc,
        track=row.track,
        metadata=bool(row.has_metadata),
        images=bool(row.has_images),
        lyrics=bool(row.has_lyrics),
        duration=row.audio_duration,
        mime_type=row.audio_mime_type or content_type_for(Path(row.path)),
        title_variants=title_variants,
        artist_variants=artist_variants,
        album_variants=album_variants,
    )


def _localized_title(row: OrganizerMediaModel, language: str) -> str:
    return select_localized_name(
        _variant_map(row.music_title_variants),
        language,
        row.title or Path(row.path).stem,
    )


def _localized_artist(row: OrganizerMediaModel, language: str) -> str:
    return select_localized_name(
        _variant_map(row.music_artist_variants),
        language,
        row.artist or "Unknown Artist",
    )


def _localized_album(row: OrganizerMediaModel, language: str) -> str:
    return select_localized_name(
        _variant_map(row.music_album_variants),
        language,
        row.album or row.title or "Unknown Album",
    )


def _localized_album_artist(row: OrganizerMediaModel, language: str) -> str:
    variants = _variant_map(row.music_album_artist_variants)
    return select_localized_name(
        variants,
        language,
        row.album_artist or _localized_artist(row, language),
    )


def _variant_map(payload: str) -> dict[str, str]:
    try:
        value = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str) and item}


def _variant_values(payload: str) -> list[str]:
    return list(_variant_map(payload).values())


def _merged_variants(
    rows: list[OrganizerMediaModel],
    field: str,
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for row in rows:
        merged.update(_variant_map(str(getattr(row, field, "{}"))))
    return merged


def _merge_canonical_track_variants(rows: list[OrganizerMediaModel]) -> None:
    grouped: dict[str, list[OrganizerMediaModel]] = {}
    for row in rows:
        grouped.setdefault(track_id_for_row(row), []).append(row)
    for track_rows in grouped.values():
        title_variants = _merged_variants(track_rows, "music_title_variants")
        artist_variants = _merged_variants(track_rows, "music_artist_variants")
        for row in track_rows:
            row.music_title_variants = json.dumps(title_variants, ensure_ascii=False)
            row.music_artist_variants = json.dumps(artist_variants, ensure_ascii=False)


def _merge_canonical_album_variants(rows: list[OrganizerMediaModel]) -> None:
    grouped: dict[str, list[OrganizerMediaModel]] = {}
    for row in rows:
        grouped.setdefault(album_id_for_row(row), []).append(row)
    for album_rows in grouped.values():
        variants = _merged_variants(album_rows, "music_album_variants")
        artist_variants = _merged_variants(
            album_rows,
            "music_album_artist_variants",
        )
        for row in album_rows:
            row.music_album_variants = json.dumps(variants, ensure_ascii=False)
            row.music_album_artist_variants = json.dumps(
                artist_variants,
                ensure_ascii=False,
            )


def _track_sort_key(row: OrganizerMediaModel) -> tuple[int, int, str]:
    return (
        row.disc or 1,
        row.track if row.track is not None else 9999,
        Path(row.path).name.casefold(),
    )
