"""Scraper facade that wires configured source adapters."""

from __future__ import annotations

from dataclasses import replace

from mm.config import CliConfig, get_config
from mm.organizer.lyrics import (
    get_lrclib_lyrics,
    search_lrclib_lyrics,
    search_netease_lyrics,
    search_qq_lyrics,
)
from mm.organizer.lyrics import (
    lyrics_from_source as _lyrics_from_source,
)
from mm.organizer.movie_scrapers import OmdbScraper, TmdbScraper
from mm.organizer.music_platform_scrapers import ItunesScraper, NeteaseScraper, QqMusicScraper
from mm.organizer.musicbrainz_scraper import MusicBrainzScraper
from mm.organizer.scraper_core import ScrapeCandidate, ScrapeQuery, Scraper

__all__ = [
    "ScrapeCandidate",
    "ScrapeQuery",
    "Scraper",
    "album_track_candidates",
    "build_scrapers",
    "configured_source_rows",
    "enrich_candidate",
    "get_lrclib_lyrics",
    "search_all",
    "search_lrclib_lyrics",
    "search_netease_lyrics",
    "search_qq_lyrics",
]

IMPLEMENTED_SOURCES = {"tmdb", "omdb", "musicbrainz", "itunes", "netease", "qqmusic"}


def build_scrapers(
    cfg: CliConfig | None = None,
    *,
    only: str | None = None,
) -> list[Scraper]:
    cfg = cfg or get_config()
    result: list[Scraper] = []
    names = [only] if only else cfg.scrapers.order
    for name in names:
        source = cfg.scrapers.sources.get(name)
        if not source or not source.enabled:
            continue
        if name == "tmdb":
            result.append(
                TmdbScraper(
                    source,
                    language=cfg.scrapers.language,
                    timeout=cfg.scrapers.timeout,
                )
            )
        elif name == "omdb":
            result.append(OmdbScraper(source, timeout=cfg.scrapers.timeout))
        elif name == "musicbrainz":
            result.append(MusicBrainzScraper(source, timeout=cfg.scrapers.timeout))
        elif name == "itunes":
            result.append(ItunesScraper(source, timeout=cfg.scrapers.timeout))
        elif name == "netease":
            result.append(NeteaseScraper(source, timeout=cfg.scrapers.timeout))
        elif name == "qqmusic":
            result.append(QqMusicScraper(source, timeout=cfg.scrapers.timeout))
    return result


def search_all(
    query: ScrapeQuery,
    *,
    cfg: CliConfig | None = None,
    source: str | None = None,
    limit: int = 5,
) -> list[ScrapeCandidate]:
    candidates: list[ScrapeCandidate] = []
    for scraper in build_scrapers(cfg, only=source):
        candidates.extend(scraper.search(query, limit=limit))
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)[:limit]


def album_track_candidates(
    candidate: ScrapeCandidate | None,
    *,
    expected_count: int | None = None,
    cfg: CliConfig | None = None,
) -> list[ScrapeCandidate]:
    if candidate is None or candidate.media_type != "album" or candidate.source == "local":
        return []
    for scraper in build_scrapers(cfg, only=candidate.source):
        album_tracks = getattr(scraper, "album_tracks", None)
        if callable(album_tracks):
            return album_tracks(candidate, expected_count=expected_count)
    return []


def enrich_candidate(
    candidate: ScrapeCandidate | None,
    *,
    query: ScrapeQuery | None = None,
    cfg: CliConfig | None = None,
) -> ScrapeCandidate | None:
    if candidate is None:
        return None
    if candidate.source != "tmdb":
        return _enrich_music_candidate(candidate, query, cfg)
    for scraper in build_scrapers(cfg, only="tmdb"):
        if isinstance(scraper, TmdbScraper):
            return scraper.details(candidate, query=query)
    return candidate


def configured_source_rows(cfg: CliConfig | None = None) -> list[list[object]]:
    cfg = cfg or get_config()
    rows: list[list[object]] = []
    for name, source in sorted(cfg.scrapers.sources.items(), key=lambda item: item[1].priority):
        has_credentials = any(value.strip() for value in source.credentials.values())
        rows.append(
            [
                name,
                "yes" if source.enabled else "no",
                "yes" if name in IMPLEMENTED_SOURCES else "pending",
                "yes" if has_credentials else "no",
                source.base_url,
            ]
        )
    return rows


def _enrich_music_candidate(
    candidate: ScrapeCandidate,
    query: ScrapeQuery | None,
    cfg: CliConfig | None,
) -> ScrapeCandidate:
    if candidate.media_type != "track":
        return candidate
    source = (cfg or get_config()).organizer.lyrics_source
    track = candidate.title or (query.title if query else "")
    artist = candidate.artist or (query.artist if query else "")
    album = candidate.album or (query.album if query else "")
    lyrics = _lyrics_from_source(source, track, artist, album)
    if not lyrics and album:
        lyrics = _lyrics_from_source(source, track, artist, "")
    if not lyrics:
        return candidate
    return replace(
        candidate,
        lyrics=str(lyrics.get("plainLyrics") or ""),
        synced_lyrics=str(lyrics.get("syncedLyrics") or ""),
    )
