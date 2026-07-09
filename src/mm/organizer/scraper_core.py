"""Shared scraper models, protocol, HTTP client, and scoring helpers."""

from __future__ import annotations

import json
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
    album: str = ""
    year: int | None = None
    disc: int | None = None
    track: int | None = None
    overview: str = ""
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


class ScraperError(RuntimeError):
    pass


class Scraper(Protocol):
    name: str

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]: ...


class HttpJsonClient:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

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
        request = urllib.request.Request(request_url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            raise ScraperError(f"HTTP {err.code} from {url}") from err
        except urllib.error.URLError as err:
            raise ScraperError(str(err.reason)) from err
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ScraperError("Unexpected JSON payload")
        return data


def confidence(query_title: str, title: str, query_year: int | None, year: int | None) -> float:
    title_score = SequenceMatcher(None, query_title.lower(), title.lower()).ratio()
    year_score = 0.08 if query_year and year and query_year == year else 0.0
    return min(1.0, round(title_score * 0.92 + year_score, 3))


def music_confidence(
    query: ScrapeQuery,
    *,
    title: str,
    artist: str,
    album: str,
) -> float:
    title_score = SequenceMatcher(None, query.title.lower(), title.lower()).ratio()
    artist_score = (
        SequenceMatcher(None, query.artist.lower(), artist.lower()).ratio()
        if query.artist and artist
        else 0.0
    )
    album_score = (
        SequenceMatcher(None, query.album.lower(), album.lower()).ratio()
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
