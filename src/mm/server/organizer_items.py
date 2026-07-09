from __future__ import annotations

import re
from functools import lru_cache

from mm.config import load_cli_config
from mm.organizer.filename import ParsedMediaFile, clean_music_title, strip_redundant_artist_prefix
from mm.server.organizer_assets import (
    _artwork_assets,
    _has_artwork,
    _has_lyrics,
    _has_subtitles,
    _related_files,
    _sidecar_lyrics,
)
from mm.server.organizer_metadata import LocalMetadata, OrganizerScanContext, _read_local_metadata
from mm.server.organizer_schemas import OrganizerItem


def _item_from_parsed(
    item: ParsedMediaFile,
    context: OrganizerScanContext | None = None,
) -> OrganizerItem:
    metadata = _read_local_metadata(item.path, item.media_type, context)
    artwork = _artwork_assets(item.path, item.media_type, context)
    related_files = _related_files(item.path, item.media_type, context)
    plain_lyrics, synced_lyrics = _sidecar_lyrics(item.path, context)
    display_artist = _display_artist(item, metadata)
    display_album = _display_album(item, metadata)
    metadata_title = _display_metadata_title(item, metadata, display_artist)
    display_title = _display_title(item, metadata_title)
    display_title = _normalize_chinese(display_title, context)
    display_artist = _normalize_chinese(display_artist, context)
    display_album = _normalize_chinese(display_album, context)
    metadata_title = _normalize_chinese(metadata_title, context)
    return OrganizerItem(
        path=str(item.path),
        media_type=item.media_type,
        title=display_title,
        artist=display_artist,
        album=display_album,
        year=metadata.year or item.year,
        season=item.season,
        episode=item.episode,
        episode_end=item.episode_end,
        disc=item.disc,
        track=item.track,
        parse_template=item.parse_template,
        parse_relative_path=item.parse_relative_path,
        confidence=item.confidence,
        metadata=metadata.exists,
        metadata_title=metadata_title,
        metadata_original_title=metadata.original_title,
        metadata_show_title=metadata.show_title,
        metadata_year=metadata.year,
        metadata_premiered=metadata.premiered,
        metadata_certification=metadata.certification,
        metadata_runtime=metadata.runtime,
        metadata_genres=metadata.genres or [],
        metadata_styles=metadata.styles or [],
        metadata_composers=metadata.composers or [],
        metadata_status=metadata.status,
        metadata_countries=metadata.countries or [],
        metadata_tagline=metadata.tagline,
        metadata_plot=metadata.plot,
        metadata_lyrics=metadata.lyrics or plain_lyrics,
        metadata_synced_lyrics=metadata.synced_lyrics or synced_lyrics,
        metadata_tags=metadata.tags or [],
        metadata_ids=metadata.ids or {},
        metadata_rating=metadata.rating,
        metadata_rating_source=metadata.rating_source,
        metadata_studios=metadata.studios or [],
        metadata_cast=metadata.cast or [],
        images=bool(artwork),
        artwork=artwork,
        subtitles=_has_subtitles(item.path, context),
        lyrics=bool(plain_lyrics or synced_lyrics) or _has_lyrics(item.path, context),
        related_files=related_files,
    )


def _light_item_from_parsed(
    item: ParsedMediaFile,
    context: OrganizerScanContext | None = None,
) -> OrganizerItem:
    local_metadata = _read_local_metadata(item.path, item.media_type, context)
    if item.media_type == "track":
        display_artist = _display_artist(item, local_metadata)
        display_album = _display_album(item, local_metadata)
        metadata_title = _display_metadata_title(item, local_metadata, display_artist)
        display_title = _display_title(item, metadata_title)
    else:
        display_title = item.title
        display_artist = item.artist
        display_album = item.album
        metadata_title = None
    display_title = _normalize_chinese(display_title, context)
    display_artist = _normalize_chinese(display_artist, context)
    display_album = _normalize_chinese(display_album, context)
    metadata_title = _normalize_chinese(metadata_title, context)
    images = _has_artwork(item.path, item.media_type, context)
    lyrics = _has_lyrics(item.path, context)
    return OrganizerItem(
        path=str(item.path),
        media_type=item.media_type,
        title=display_title or item.title,
        artist=display_artist,
        album=display_album,
        year=local_metadata.year or item.year,
        season=item.season,
        episode=item.episode,
        episode_end=item.episode_end,
        disc=item.disc,
        track=item.track,
        parse_template=item.parse_template,
        parse_relative_path=item.parse_relative_path,
        confidence=item.confidence,
        metadata=local_metadata.exists,
        metadata_title=metadata_title,
        metadata_original_title=local_metadata.original_title,
        metadata_show_title=local_metadata.show_title,
        metadata_year=local_metadata.year,
        metadata_premiered=local_metadata.premiered,
        metadata_certification=local_metadata.certification,
        metadata_runtime=local_metadata.runtime,
        metadata_genres=local_metadata.genres or [],
        metadata_styles=local_metadata.styles or [],
        metadata_composers=local_metadata.composers or [],
        metadata_status=local_metadata.status,
        metadata_countries=local_metadata.countries or [],
        metadata_tagline=local_metadata.tagline,
        metadata_plot=local_metadata.plot,
        metadata_tags=local_metadata.tags or [],
        metadata_ids=local_metadata.ids or {},
        metadata_rating=local_metadata.rating,
        metadata_rating_source=local_metadata.rating_source,
        metadata_studios=local_metadata.studios or [],
        metadata_cast=local_metadata.cast or [],
        images=images,
        subtitles=_has_subtitles(item.path, context),
        lyrics=bool(local_metadata.lyrics or local_metadata.synced_lyrics) or lyrics,
    )


def _display_metadata_title(
    item: ParsedMediaFile,
    metadata: LocalMetadata,
    artist: str | None,
) -> str | None:
    if not metadata.title:
        return None
    if item.media_type == "track" and not item.path.with_suffix(".nfo").exists():
        return None
    if item.media_type == "track":
        if item.parse_template:
            return item.title
        title = strip_redundant_artist_prefix(metadata.title, artist)
        if _same_title(title, metadata.album) or _same_title(title, item.album):
            return item.title
        return title
    return metadata.title


def _display_artist(item: ParsedMediaFile, metadata: LocalMetadata) -> str | None:
    return metadata.artist or item.artist


def _display_album(item: ParsedMediaFile, metadata: LocalMetadata) -> str | None:
    if item.media_type == "album":
        return clean_music_title(metadata.title or metadata.album or item.album)
    return clean_music_title(metadata.album or item.album)


def _display_title(item: ParsedMediaFile, metadata_title: str | None) -> str:
    return metadata_title or item.title


def _same_title(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return _normalized_title(left) == _normalized_title(right)


def _same_album_title(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return _normalized_title(left) == _normalized_title(_strip_leading_year(right))


def _strip_leading_year(value: str) -> str:
    return re.sub(r"^(?:19\d{2}|20\d{2}|2100)\s*[-–—_. ]+\s*", "", value).strip()


def _normalized_title(value: str) -> str:
    return re.sub(r"[_\W]+", " ", value.lower()).strip()


def _normalize_chinese(value: str | None, context: OrganizerScanContext | None) -> str | None:
    if not value:
        return value
    script = context.chinese_script if context else load_cli_config().organizer.chinese_script
    if script not in {"simplified", "traditional"}:
        return value
    converter = _opencc_converter("t2s" if script == "simplified" else "s2t")
    if converter is None:
        return value
    return converter.convert(value)


@lru_cache(maxsize=2)
def _opencc_converter(config: str):  # noqa: ANN202 - optional dependency type
    try:
        from opencc import OpenCC
    except ImportError:
        return None
    return OpenCC(config)
