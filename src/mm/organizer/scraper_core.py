"""Shared scraper models, protocol, HTTP client, and scoring helpers."""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Protocol


@dataclass(frozen=True)
class ScrapeQuery:
    media_type: str
    title: str
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    track: int | None = None


@dataclass(frozen=True)
class ScrapeCandidate:
    source: str
    source_id: str
    media_type: str
    title: str
    original_title: str = ""
    show_title: str = ""
    artist: str = ""
    album_artist: str = ""
    album: str = ""
    year: int | None = None
    disc: int | None = None
    track: int | None = None
    overview: str = ""
    tagline: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    logo_url: str = ""
    trailer_url: str = ""
    release_date: str = ""
    certification: str = ""
    runtime: int | None = None
    status: str = ""
    original_language: str = ""
    genres: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    composers: list[str] = field(default_factory=list)
    external_ids: dict[str, str] = field(default_factory=dict)
    cast: list[dict[str, str]] = field(default_factory=list)
    crew: list[dict[str, str]] = field(default_factory=list)
    lyrics: str = ""
    synced_lyrics: str = ""
    rating: float | None = None
    confidence: float = 0.0
    title_variants: dict[str, str] = field(default_factory=dict)
    artist_variants: dict[str, str] = field(default_factory=dict)
    album_artist_variants: dict[str, str] = field(default_factory=dict)
    album_variants: dict[str, str] = field(default_factory=dict)


class ScraperError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class Scraper(Protocol):
    name: str

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]: ...


_USER_AGENT = "litemm/1.0 (+https://github.com/HSPK/mm)"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Minimum seconds between requests per host. MusicBrainz mandates <= 1 req/s
# with a descriptive User-Agent; other public APIs get a light default spacing.
_HOST_MIN_INTERVAL = {"musicbrainz.org": 1.05}
_DEFAULT_MIN_INTERVAL = 0.2
_RATE_GUARD = threading.Lock()
_RATE_LOCKS: dict[str, threading.Lock] = {}
_LAST_REQUEST: dict[str, float] = {}


def _host_min_interval(host: str) -> float:
    for key, interval in _HOST_MIN_INTERVAL.items():
        if key in host:
            return interval
    return _DEFAULT_MIN_INTERVAL


def _throttle(host: str) -> None:
    """Serialize + space out requests per host to respect API rate limits."""
    with _RATE_GUARD:
        lock = _RATE_LOCKS.setdefault(host, threading.Lock())
    with lock:
        interval = _host_min_interval(host)
        wait = interval - (time.monotonic() - _LAST_REQUEST.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST[host] = time.monotonic()


class HttpJsonClient:
    def __init__(self, timeout: float, *, max_retries: int = 2, backoff: float = 0.6) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    def get(
        self,
        url: str,
        params: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode(
            {key: value for key, value in params.items() if value is not None and value != ""}
        )
        request_url = f"{url}?{query}" if query else url
        host = urllib.parse.urlparse(url).netloc
        request_headers = {"User-Agent": _USER_AGENT, **(headers or {})}
        last_error: ScraperError | None = None
        for attempt in range(self.max_retries + 1):
            _throttle(host)
            try:
                data = self._fetch(request_url, request_headers)
            except ScraperError as err:
                last_error = err
                if not err.retryable or attempt >= self.max_retries:
                    raise
                time.sleep(min(self.backoff * (2**attempt), 8.0))
                continue
            if not isinstance(data, dict):
                raise ScraperError("Unexpected JSON payload")
            return data
        raise last_error or ScraperError("Request failed")

    def _fetch(self, request_url: str, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(request_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            raise ScraperError(
                f"HTTP {err.code} from {request_url}",
                retryable=err.code in _RETRYABLE_STATUS,
            ) from err
        except (urllib.error.URLError, TimeoutError) as err:
            reason = getattr(err, "reason", err)
            raise ScraperError(str(reason), retryable=True) from err
        return json.loads(payload)


def _normalize_score(value: str) -> str:
    """Normalize a title for fuzzy scoring: fold case/width/accents, drop
    featured-artist credits, bracketed qualifiers, and punctuation. Keeps CJK
    (word) characters so Chinese titles still compare cleanly."""
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\b(?:feat\.?|ft\.?|featuring)\b.*$", " ", text)
    text = re.sub(r"[\[\(（【].*?[\]\)）】]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def confidence(query_title: str, title: str, query_year: int | None, year: int | None) -> float:
    title_score = SequenceMatcher(
        None, _normalize_score(query_title), _normalize_score(title)
    ).ratio()
    year_score = 0.08 if query_year and year and query_year == year else 0.0
    return min(1.0, round(title_score * 0.92 + year_score, 3))


def music_confidence(
    query: ScrapeQuery,
    *,
    title: str,
    artist: str,
    album: str,
) -> float:
    title_score = SequenceMatcher(
        None, _normalize_score(query.title), _normalize_score(title)
    ).ratio()
    artist_score = (
        SequenceMatcher(None, _normalize_score(query.artist), _normalize_score(artist)).ratio()
        if query.artist and artist
        else 0.0
    )
    album_score = (
        SequenceMatcher(None, _normalize_score(query.album), _normalize_score(album)).ratio()
        if query.album and album
        else 0.0
    )
    weighted = title_score * 0.64 + artist_score * 0.24 + album_score * 0.12
    return min(1.0, round(weighted, 3))


def year_from_date(value: str) -> int | None:
    if len(value) < 4:
        return None
    try:
        year = int(value[:4])
    except ValueError:
        return None
    return year if 1800 <= year <= 2200 else None


def int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def int_from_value(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def normalize_for_match(value: str) -> str:
    return " ".join(value.lower().split())
