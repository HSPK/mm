"""MusicBrainz scraper adapter."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from mm.config import ScraperSourceConfig
from mm.organizer.localization import localized_variants, select_localized_name
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

    def __init__(
        self,
        source: ScraperSourceConfig,
        *,
        timeout: float,
        language: str = "en",
    ) -> None:
        self.source = source
        self.client = HttpJsonClient(timeout)
        self.language = language
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
            title_variants = localized_variants(title)
            artist_variants = localized_variants(artist)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(item["id"]),
                    media_type="album",
                    title=title,
                    artist=artist,
                    album_artist=artist,
                    year=year,
                    poster_url=f"https://coverartarchive.org/release-group/{item['id']}/front-250",
                    genres=_musicbrainz_names(item.get("genres")),
                    styles=_musicbrainz_names(item.get("tags")),
                    tags=_musicbrainz_names(item.get("tags")),
                    confidence=_musicbrainz_confidence(
                        item,
                        query,
                        title=title,
                        artist=artist,
                        album=title,
                    ),
                    external_ids={
                        "musicbrainz_release_group": str(item["id"]),
                        **_artist_external_id(item),
                        **_album_artist_external_id(item),
                    },
                    title_variants=title_variants,
                    artist_variants=artist_variants,
                    album_artist_variants=artist_variants,
                    album_variants=title_variants,
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
            title_variants = localized_variants(title)
            artist_variants = localized_variants(artist)
            album_variants = localized_variants(album)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(item["id"]),
                    media_type="track",
                    title=title,
                    artist=artist,
                    album_artist=artist,
                    album=album,
                    year=year,
                    genres=_musicbrainz_names(item.get("genres")),
                    styles=_musicbrainz_names(item.get("tags")),
                    tags=_musicbrainz_names(item.get("tags")),
                    composers=_composer_names(item),
                    confidence=_musicbrainz_confidence(
                        item,
                        query,
                        title=title,
                        artist=artist,
                        album=album,
                    ),
                    external_ids={
                        "musicbrainz_recording": str(item["id"]),
                        **_artist_external_id(item),
                        **_release_external_ids(release),
                    },
                    title_variants=title_variants,
                    artist_variants=artist_variants,
                    album_artist_variants=artist_variants,
                    album_variants=album_variants,
                )
            )
        return candidates

    def details(
        self,
        candidate: ScrapeCandidate,
        *,
        query: ScrapeQuery | None = None,
    ) -> ScrapeCandidate:
        entity = "release-group" if candidate.media_type == "album" else "recording"
        data = self.client.get(
            f"{self.source.base_url.rstrip('/')}/{entity}/{candidate.source_id}",
            {
                "fmt": "json",
                "inc": "aliases+artist-credits+genres+tags+releases",
            },
            {"User-Agent": self.user_agent},
        )
        title = str(data.get("title") or candidate.title)
        title_variants = localized_variants(title, data.get("aliases"))
        credits = _artist_credits(data)
        if not credits and candidate.external_ids.get("musicbrainz_artist"):
            credits = [
                (
                    candidate.artist,
                    candidate.external_ids["musicbrainz_artist"],
                )
            ]
        artist = ", ".join(name for name, _artist_id_value in credits if name)
        artist = artist or candidate.artist
        credit_variants: list[tuple[str, dict[str, str]]] = []
        for credit_name, artist_id in credits:
            variants = localized_variants(credit_name)
            if not artist_id:
                credit_variants.append((credit_name, variants))
                continue
            artist_data = self.client.get(
                f"{self.source.base_url.rstrip('/')}/artist/{artist_id}",
                {"fmt": "json", "inc": "aliases"},
                {"User-Agent": self.user_agent},
            )
            canonical_name = str(artist_data.get("name") or credit_name)
            credit_variants.append(
                (
                    canonical_name,
                    localized_variants(canonical_name, artist_data.get("aliases")),
                )
            )
        artist_variants = _combine_artist_variants(credit_variants)
        album_variants = (
            title_variants
            if candidate.media_type == "album"
            else candidate.album_variants or localized_variants(candidate.album)
        )
        localized_title = select_localized_name(
            title_variants,
            self.language,
            title,
        )
        localized_artist = select_localized_name(
            artist_variants,
            self.language,
            artist,
        )
        localized_album = select_localized_name(
            album_variants,
            self.language,
            candidate.album,
        )
        external_ids = {
            **candidate.external_ids,
            f"musicbrainz_{'release_group' if entity == 'release-group' else 'recording'}": (
                candidate.source_id
            ),
        }
        artist_ids = [artist_id for _name, artist_id in credits if artist_id]
        if artist_ids:
            external_ids["musicbrainz_artist"] = artist_ids[0]
            external_ids["musicbrainz_artist_credit"] = "+".join(artist_ids)
            if candidate.media_type == "album":
                external_ids["musicbrainz_album_artist_credit"] = "+".join(artist_ids)
        return replace(
            candidate,
            title=localized_title,
            original_title=(
                candidate.original_title or (title if localized_title != title else "")
            ),
            artist=localized_artist,
            album_artist=(
                localized_artist if candidate.media_type == "album" else candidate.album_artist
            ),
            album=localized_album,
            genres=_musicbrainz_names(data.get("genres")) or candidate.genres,
            tags=_musicbrainz_names(data.get("tags")) or candidate.tags,
            external_ids=external_ids,
            title_variants=title_variants,
            artist_variants=artist_variants,
            album_artist_variants=(
                artist_variants
                if candidate.media_type == "album"
                else candidate.album_artist_variants
            ),
            album_variants=album_variants,
        )

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
        artist = _artist_credit(recording) or album.artist
        artist_variants = (
            localized_variants(artist) if _artist_credit(recording) else album.artist_variants
        )
        result.append(
            ScrapeCandidate(
                source=album.source,
                source_id=str(recording.get("id") or f"{album.source_id}:{disc}:{index}"),
                media_type="track",
                title=title,
                artist=artist,
                album_artist=album.album_artist or album.artist,
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
                external_ids={
                    **album.external_ids,
                    **_artist_external_id(recording),
                    "musicbrainz_recording": str(
                        recording.get("id") or f"{album.source_id}:{disc}:{index}"
                    ),
                },
                title_variants=localized_variants(title),
                artist_variants=artist_variants,
                album_artist_variants=album.album_artist_variants or album.artist_variants,
                album_variants=album.album_variants or album.title_variants,
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


def _artist_credits(item: dict[str, Any]) -> list[tuple[str, str]]:
    credits = item.get("artist-credit")
    if not isinstance(credits, list):
        return []
    result: list[tuple[str, str]] = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        artist = credit.get("artist")
        artist = artist if isinstance(artist, dict) else {}
        name = str(credit.get("name") or artist.get("name") or "")
        artist_id = str(artist.get("id") or "")
        if name:
            result.append((name, artist_id))
    return result


def _artist_external_id(item: dict[str, Any]) -> dict[str, str]:
    artist_ids = [artist_id for _name, artist_id in _artist_credits(item) if artist_id]
    if not artist_ids:
        return {}
    return {
        "musicbrainz_artist": artist_ids[0],
        "musicbrainz_artist_credit": "+".join(artist_ids),
    }


def _album_artist_external_id(item: dict[str, Any]) -> dict[str, str]:
    artist_ids = [artist_id for _name, artist_id in _artist_credits(item) if artist_id]
    return {"musicbrainz_album_artist_credit": "+".join(artist_ids)} if artist_ids else {}


def _combine_artist_variants(
    credits: list[tuple[str, dict[str, str]]],
) -> dict[str, str]:
    if not credits:
        return {}
    locales = {"und"}
    for _name, variants in credits:
        locales.update(variants)
    return {
        locale: ", ".join(
            select_localized_name(variants, locale, name) for name, variants in credits
        )
        for locale in locales
    }


def _release_external_ids(release: Any) -> dict[str, str]:
    if not isinstance(release, dict):
        return {}
    ids: dict[str, str] = {}
    if release.get("id"):
        ids["musicbrainz_release"] = str(release["id"])
    release_group = release.get("release-group")
    if isinstance(release_group, dict) and release_group.get("id"):
        ids["musicbrainz_release_group"] = str(release_group["id"])
    return ids


def _musicbrainz_confidence(
    item: dict[str, Any],
    query: ScrapeQuery,
    *,
    title: str,
    artist: str,
    album: str,
) -> float:
    local_score = music_confidence(query, title=title, artist=artist, album=album)
    try:
        server_score = float(item.get("score") or 0) / 100
    except (TypeError, ValueError):
        server_score = 0
    return max(local_score, min(1.0, round(server_score * 0.95, 3)))


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
