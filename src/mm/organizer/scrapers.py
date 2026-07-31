"""Scraper facade that wires configured source adapters."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from mm.config import CliConfig, ScraperSourceConfig, get_config
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
    "album_signature_candidates",
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

ScraperFactory = Callable[[ScraperSourceConfig, CliConfig], Scraper]


def _tmdb_factory(source: ScraperSourceConfig, cfg: CliConfig) -> Scraper:
    return TmdbScraper(
        source,
        language=cfg.scrapers.language,
        timeout=cfg.scrapers.timeout,
    )


def _musicbrainz_factory(source: ScraperSourceConfig, cfg: CliConfig) -> Scraper:
    return MusicBrainzScraper(
        source,
        timeout=cfg.scrapers.timeout,
        language=cfg.scrapers.language,
    )


def _itunes_factory(source: ScraperSourceConfig, cfg: CliConfig) -> Scraper:
    return ItunesScraper(
        source,
        timeout=cfg.scrapers.timeout,
        language=cfg.scrapers.language,
    )


def _timeout_factory(scraper_type) -> ScraperFactory:
    return lambda source, cfg: scraper_type(source, timeout=cfg.scrapers.timeout)


SCRAPER_FACTORIES: dict[str, ScraperFactory] = {
    "tmdb": _tmdb_factory,
    "omdb": _timeout_factory(OmdbScraper),
    "musicbrainz": _musicbrainz_factory,
    "itunes": _itunes_factory,
    "netease": _timeout_factory(NeteaseScraper),
    "qqmusic": _timeout_factory(QqMusicScraper),
}
IMPLEMENTED_SOURCES = frozenset(SCRAPER_FACTORIES)


def register_scraper(name: str, factory: ScraperFactory) -> None:
    SCRAPER_FACTORIES[name] = factory


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
        factory = SCRAPER_FACTORIES.get(name)
        if factory:
            result.append(factory(source, cfg))
    return result


def search_all(
    query: ScrapeQuery,
    *,
    cfg: CliConfig | None = None,
    source: str | None = None,
    limit: int = 5,
) -> list[ScrapeCandidate]:
    scrapers = build_scrapers(cfg, only=source)
    if not scrapers:
        return []
    # Each source is a distinct host with its own rate-limit lock, so query them
    # concurrently: wall time drops from the sum of per-source latencies to the
    # slowest single source. A source that errors is isolated so the others'
    # results are still used; only a total wipeout (every source failed) is
    # surfaced as an error instead of a misleading "no match".
    if len(scrapers) == 1:
        outcomes = [_run_scraper_search(scrapers[0], query, limit)]
    else:
        with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
            outcomes = list(
                pool.map(lambda scraper: _run_scraper_search(scraper, query, limit), scrapers)
            )
    candidates: list[ScrapeCandidate] = []
    errors: list[Exception] = []
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            errors.append(outcome)
        else:
            candidates.extend(outcome)
    if not candidates and len(errors) == len(scrapers):
        raise errors[0]
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)[:limit]


def _run_scraper_search(
    scraper: Scraper,
    query: ScrapeQuery,
    limit: int,
) -> list[ScrapeCandidate] | Exception:
    try:
        return list(scraper.search(query, limit=limit))
    except Exception as exc:  # noqa: BLE001 - isolate one source; others still count
        return exc


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


def album_signature_candidates(
    query: ScrapeQuery,
    durations: list[float],
    *,
    cfg: CliConfig | None = None,
    source: str | None = None,
) -> tuple[ScrapeCandidate, list[ScrapeCandidate]] | None:
    if source not in {None, "netease"}:
        return None
    for scraper in build_scrapers(cfg, only="netease"):
        album_by_signature = getattr(scraper, "album_by_signature", None)
        if callable(album_by_signature):
            return album_by_signature(query, durations)
    return None


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
    config = cfg or get_config()
    enriched = candidate
    for scraper in build_scrapers(config, only=candidate.source):
        details = getattr(scraper, "details", None)
        if callable(details):
            enriched = details(candidate, query=query)
            break
    if enriched.media_type != "track":
        return enriched
    source = config.organizer.lyrics_source
    track = enriched.title or (query.title if query else "")
    artist = enriched.artist or (query.artist if query else "")
    album = enriched.album or (query.album if query else "")
    lyrics = None
    if source == "all":
        sources = ("lrclib", "netease", "kugou", "qq")
    elif source == "qq":
        sources = ("lrclib", "netease", "kugou")
    else:
        sources = tuple(dict.fromkeys((source, "lrclib", "netease", "kugou", "qq")))
    for lyrics_source in sources:
        lyrics = _lyrics_from_source(lyrics_source, track, artist, album)
        if not lyrics and album:
            lyrics = _lyrics_from_source(lyrics_source, track, artist, "")
        if lyrics:
            break
    if not lyrics:
        return enriched
    return replace(
        enriched,
        lyrics=str(lyrics.get("plainLyrics") or ""),
        synced_lyrics=str(lyrics.get("syncedLyrics") or ""),
    )
