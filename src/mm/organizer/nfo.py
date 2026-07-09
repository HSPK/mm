"""Kodi/Jellyfin-compatible minimal NFO generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate


@dataclass(frozen=True)
class NfoDocument:
    target: Path
    xml: str
    media_type: str


def build_nfo(item: ParsedMediaFile, candidate: ScrapeCandidate | None = None) -> NfoDocument:
    if item.media_type == "movie":
        root = ET.Element("movie")
        target = item.path.with_suffix(".nfo")
    elif item.media_type == "tv":
        root = ET.Element("episodedetails")
        target = item.path.with_suffix(".nfo")
    elif item.media_type in {"album", "track"}:
        root = ET.Element("album" if item.media_type == "album" else "song")
        target = item.path.with_suffix(".nfo")
    else:
        raise ValueError(f"Unsupported media type: {item.media_type}")

    _add(root, "title", _item_title(item, candidate))
    if candidate and candidate.original_title:
        _add(root, "originaltitle", candidate.original_title)
    year = candidate.year if candidate and candidate.year else item.year
    if year:
        _add(root, "year", str(year))
    if candidate and candidate.release_date:
        _add(root, "premiered", candidate.release_date)
    if candidate and candidate.certification:
        _add(root, "mpaa", candidate.certification)
    if candidate and candidate.runtime:
        _add(root, "runtime", str(candidate.runtime))
    if candidate and candidate.status:
        _add(root, "status", candidate.status)
    if candidate and candidate.original_language:
        _add(root, "original_language", candidate.original_language)
    if candidate and candidate.rating is not None:
        ratings = ET.SubElement(root, "ratings")
        rating = ET.SubElement(ratings, "rating", {"name": candidate.source, "default": "true"})
        _add(rating, "value", f"{candidate.rating:.1f}")
    if candidate:
        for genre in candidate.genres:
            _add(root, "genre", genre)
        for country in candidate.countries:
            _add(root, "country", country)
        for studio in candidate.studios:
            _add(root, "studio", studio)
        for tag in candidate.tags:
            _add(root, "tag", tag)
        if candidate.trailer_url:
            _add(root, "trailer", candidate.trailer_url)
        if candidate.backdrop_url:
            fanart = ET.SubElement(root, "fanart")
            _add(fanart, "thumb", candidate.backdrop_url)
        if candidate.logo_url:
            _add(root, "clearlogo", candidate.logo_url)
    if candidate and candidate.overview:
        _add(root, "plot", candidate.overview)
    if candidate:
        unique = ET.SubElement(root, "uniqueid", {"type": candidate.source, "default": "true"})
        unique.text = candidate.source_id
        for source, source_id in candidate.external_ids.items():
            if source_id:
                extra = ET.SubElement(root, "uniqueid", {"type": source, "default": "false"})
                extra.text = source_id
        if candidate.poster_url:
            _add(root, "thumb", candidate.poster_url)

    if item.media_type == "tv":
        if item.season is not None:
            _add(root, "season", str(item.season))
        if item.episode is not None:
            _add(root, "episode", str(item.episode))
        show_title = candidate.show_title if candidate and candidate.show_title else item.title
        _add(root, "showtitle", show_title)
    elif item.media_type in {"album", "track"}:
        artist = candidate.artist if candidate and candidate.artist else item.artist
        album = _album_title(item, candidate)
        if artist:
            _add(root, "artist", artist)
        if album:
            _add(root, "album", album)
        if candidate:
            for composer in candidate.composers:
                _add(root, "composer", composer)
            for style in candidate.styles:
                _add(root, "style", style)
            for genre in candidate.genres:
                _add(root, "genre", genre)
            lyrics = candidate.synced_lyrics or candidate.lyrics
            if lyrics:
                _add(root, "lyrics", lyrics)
        if item.track:
            _add(root, "track", str(item.track))
        if item.disc:
            _add(root, "disc", str(item.disc))

    if candidate:
        for actor in candidate.cast:
            node = ET.SubElement(root, "actor")
            _add(node, "name", actor.get("name", ""))
            if actor.get("role"):
                _add(node, "role", actor["role"])
        for person in candidate.crew:
            job = person.get("job", "").lower()
            if "director" in job:
                _add(root, "director", person.get("name", ""))
            elif "writer" in job or "screenplay" in job:
                _add(root, "credits", person.get("name", ""))
            elif "producer" in job:
                _add(root, "producer", person.get("name", ""))

    return NfoDocument(target=target, xml=_serialize(root), media_type=item.media_type)


def build_album_nfo(item: ParsedMediaFile, candidate: ScrapeCandidate | None = None) -> NfoDocument:
    root = ET.Element("album")
    target = item.path.parent / "album.nfo"
    title = _album_title(item, candidate) or item.path.parent.name
    _add(root, "title", title)
    artist = candidate.artist if candidate and candidate.artist else item.artist
    if artist:
        _add(root, "artist", artist)
    year = candidate.year if candidate and candidate.year else item.year
    if year:
        _add(root, "year", str(year))
    if candidate and candidate.overview:
        _add(root, "review", candidate.overview)
    if candidate:
        for genre in candidate.genres:
            _add(root, "genre", genre)
        for style in candidate.styles:
            _add(root, "style", style)
        for composer in candidate.composers:
            _add(root, "composer", composer)
    if candidate:
        unique = ET.SubElement(root, "uniqueid", {"type": candidate.source, "default": "true"})
        unique.text = candidate.source_id
        if candidate.poster_url:
            _add(root, "thumb", candidate.poster_url)
    return NfoDocument(target=target, xml=_serialize(root), media_type="album")


def build_tvshow_nfo(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None = None,
) -> NfoDocument:
    root = ET.Element("tvshow")
    target = _tvshow_root(item.path) / "tvshow.nfo"
    _add(root, "title", candidate.title if candidate else item.title)
    if candidate and candidate.original_title:
        _add(root, "originaltitle", candidate.original_title)
    if candidate and candidate.year:
        _add(root, "year", str(candidate.year))
    if candidate and candidate.overview:
        _add(root, "plot", candidate.overview)
    if candidate:
        for genre in candidate.genres:
            _add(root, "genre", genre)
        for studio in candidate.studios:
            _add(root, "studio", studio)
        for country in candidate.countries:
            _add(root, "country", country)
        if candidate.status:
            _add(root, "status", candidate.status)
        if candidate.poster_url:
            _add(root, "thumb", candidate.poster_url)
        if candidate.backdrop_url:
            fanart = ET.SubElement(root, "fanart")
            _add(fanart, "thumb", candidate.backdrop_url)
    return NfoDocument(target=target, xml=_serialize(root), media_type="tvshow")


def _tvshow_root(path: Path) -> Path:
    parent = path.parent
    if parent.name.lower().startswith("season"):
        return parent.parent
    return parent


def _item_title(item: ParsedMediaFile, candidate: ScrapeCandidate | None) -> str:
    if not candidate:
        return item.title
    if item.media_type == "track" and candidate.media_type == "album":
        return item.title
    return candidate.title


def _album_title(item: ParsedMediaFile, candidate: ScrapeCandidate | None) -> str | None:
    if candidate and candidate.media_type == "album":
        return candidate.title
    if candidate and candidate.album:
        return candidate.album
    return item.album


def write_nfo(document: NfoDocument, *, overwrite: bool = False) -> None:
    if document.target.exists() and not overwrite:
        raise FileExistsError(document.target)
    document.target.write_text(document.xml, encoding="utf-8")


def _add(root: ET.Element, tag: str, value: str) -> None:
    child = ET.SubElement(root, tag)
    child.text = value


def _serialize(root: ET.Element) -> str:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
