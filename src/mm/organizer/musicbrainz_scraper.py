"""MusicBrainz scraper adapter."""

from __future__ import annotations

from typing import Any

from mm.config import ScraperSourceConfig
from mm.organizer.scraper_core import (
    HttpJsonClient,
    ScrapeCandidate,
    ScrapeQuery,
    int_from_value,
    music_confidence,
    normalize_for_match,
    year_from_date,
)


class MusicBrainzScraper:
    name = "musicbrainz"

    def __init__(self, source: ScraperSourceConfig, *, timeout: float) -> None:
        self.source = source
        self.client = HttpJsonClient(timeout)
        self.user_agent = (
            source.credentials.get("user_agent", "").strip()
            or "litemm/0.1 (https://github.com/HSPK/mm)"
        )

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        if query.media_type == "album":
            return self._search_album(query, limit=limit)
        if query.media_type == "track":
            return self._search_track(query, limit=limit)
        return []

    def _search_album(self, query: ScrapeQuery, *, limit: int) -> list[ScrapeCandidate]:
        data = self.client.get(
            f"{self.source.base_url.rstrip('/')}/release-group/",
            {
                "query": _musicbrainz_query(release=query.title, artist=query.artist),
                "fmt": "json",
                "limit": limit,
            },
            {"User-Agent": self.user_agent},
        )
        raw_results = data.get("release-groups", [])
        if not isinstance(raw_results, list):
            return []
        candidates: list[ScrapeCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            title = str(item.get("title") or "")
            year = year_from_date(str(item.get("first-release-date") or ""))
            artist = _artist_credit(item)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(item["id"]),
                    media_type="album",
                    title=title,
                    artist=artist,
                    year=year,
                    poster_url=f"https://coverartarchive.org/release-group/{item['id']}/front-250",
                    genres=_musicbrainz_names(item.get("genres")),
                    styles=_musicbrainz_names(item.get("tags")),
                    tags=_musicbrainz_names(item.get("tags")),
                    confidence=music_confidence(query, title=title, artist=artist, album=title),
                )
            )
        return candidates

    def _search_track(self, query: ScrapeQuery, *, limit: int) -> list[ScrapeCandidate]:
        data = self.client.get(
            f"{self.source.base_url.rstrip('/')}/recording/",
            {
                "query": _musicbrainz_query(
                    recording=query.title,
                    artist=query.artist,
                    release=query.album,
                ),
                "fmt": "json",
                "limit": limit,
            },
            {"User-Agent": self.user_agent},
        )
        raw_results = data.get("recordings", [])
        if not isinstance(raw_results, list):
            return []
        candidates: list[ScrapeCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            title = str(item.get("title") or "")
            artist = _artist_credit(item)
            releases = item.get("releases")
            release = releases[0] if isinstance(releases, list) and releases else {}
            album = str(release.get("title") or "") if isinstance(release, dict) else ""
            year = (
                year_from_date(str(release.get("date") or ""))
                if isinstance(release, dict)
                else None
            )
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(item["id"]),
                    media_type="track",
                    title=title,
                    artist=artist,
                    album=album,
                    year=year,
                    genres=_musicbrainz_names(item.get("genres")),
                    styles=_musicbrainz_names(item.get("tags")),
                    tags=_musicbrainz_names(item.get("tags")),
                    composers=_composer_names(item),
                    confidence=music_confidence(query, title=title, artist=artist, album=album),
                )
            )
        return candidates

    def album_tracks(
        self,
        candidate: ScrapeCandidate,
        *,
        expected_count: int | None = None,
    ) -> list[ScrapeCandidate]:
        data = self.client.get(
            f"{self.source.base_url.rstrip('/')}/release/",
            {
                "release-group": candidate.source_id,
                "fmt": "json",
                "inc": "media+recordings",
                "limit": 25,
            },
            {"User-Agent": self.user_agent},
        )
        releases = data.get("releases", [])
        if not isinstance(releases, list):
            return []
        media = _best_track_media(releases, candidate, expected_count)
        return _track_candidates(candidate, media) if media else []


def _musicbrainz_query(**fields: str | None) -> str:
    return " AND ".join(
        f'{key}:"{value}"' for key, value in fields.items() if value and value.strip()
    )


def _best_track_media(
    releases: list[Any],
    candidate: ScrapeCandidate,
    expected_count: int | None,
) -> dict[str, Any] | None:
    options: list[tuple[int, dict[str, Any]]] = []
    candidate_title = normalize_for_match(candidate.title)
    for release in releases:
        if not isinstance(release, dict):
            continue
        release_title = normalize_for_match(str(release.get("title") or ""))
        release_status = str(release.get("status") or "").lower()
        release_country = str(release.get("country") or "").upper()
        release_year = year_from_date(str(release.get("date") or ""))
        for media in release.get("media", []):
            if not isinstance(media, dict):
                continue
            tracks = media.get("tracks", [])
            if not isinstance(tracks, list) or not tracks:
                continue
            score = _track_count_score(
                int_from_value(media.get("track-count")) or len(tracks), expected_count
            )
            score += (
                5
                if release_title == candidate_title
                else 2
                if candidate_title in release_title
                else 0
            )
            score += 4 if release_status == "official" else 0
            score += (
                4
                if release_country in {"TW", "CN", "HK", "SG"}
                else -4
                if release_country == "JP"
                else 0
            )
            if candidate.year and release_year == candidate.year:
                score += 3
            elif candidate.year and release_year:
                score -= min(3, abs(release_year - candidate.year))
            score += 1 if str(media.get("format") or "").lower() == "cd" else 0
            score += 1 if _contains_cjk(str(release.get("title") or "")) else 0
            score -= 3 if _media_contains_kana(media) else 0
            options.append((score, media))
    return max(options, key=lambda item: item[0])[1] if options else None


def _track_count_score(track_count: int, expected_count: int | None) -> int:
    if expected_count and track_count == expected_count:
        return 8
    if expected_count:
        return -abs(track_count - expected_count)
    return 0


def _track_candidates(album: ScrapeCandidate, media: dict[str, Any]) -> list[ScrapeCandidate]:
    tracks = media.get("tracks", [])
    if not isinstance(tracks, list):
        return []
    result: list[ScrapeCandidate] = []
    disc = int_from_value(media.get("position")) or 1
    for index, track in enumerate(tracks, start=1):
        if not isinstance(track, dict):
            continue
        title = str(track.get("title") or "")
        if not title:
            continue
        recording = track.get("recording")
        recording = recording if isinstance(recording, dict) else {}
        result.append(
            ScrapeCandidate(
                source=album.source,
                source_id=str(recording.get("id") or f"{album.source_id}:{disc}:{index}"),
                media_type="track",
                title=title,
                artist=_artist_credit(recording) or album.artist,
                album=album.album or album.title,
                year=album.year,
                disc=disc,
                track=int_from_value(track.get("number")) or index,
                poster_url=album.poster_url,
                genres=album.genres,
                styles=album.styles,
                tags=album.tags,
                composers=album.composers,
                confidence=1,
            )
        )
    return result


def _artist_credit(item: dict[str, Any]) -> str:
    credits = item.get("artist-credit")
    if not isinstance(credits, list):
        return ""
    return ", ".join(
        str(credit.get("name"))
        for credit in credits
        if isinstance(credit, dict) and isinstance(credit.get("name"), str)
    )


def _musicbrainz_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item.get("name")) for item in value if isinstance(item, dict) and item.get("name")][
        :12
    ]


def _composer_names(item: dict[str, Any]) -> list[str]:
    relations = item.get("relations")
    if not isinstance(relations, list):
        return []
    names: list[str] = []
    for relation in relations:
        if not isinstance(relation, dict) or relation.get("type") not in {"composer", "writer"}:
            continue
        artist = relation.get("artist")
        if isinstance(artist, dict) and artist.get("name"):
            names.append(str(artist["name"]))
    return names


def _contains_cjk(value: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in value)


def _media_contains_kana(media: dict[str, Any]) -> bool:
    tracks = media.get("tracks", [])
    if not isinstance(tracks, list):
        return False
    return any(
        any("\u3040" <= char <= "\u30ff" for char in str(track.get("title") or ""))
        for track in tracks
        if isinstance(track, dict)
    )
