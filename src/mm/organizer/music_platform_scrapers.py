"""Music platform scraper adapters for iTunes, NetEase, and QQ Music."""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mm.config import ScraperSourceConfig
from mm.organizer.localization import canonicalize_music_artist, localized_variants
from mm.organizer.scraper_core import (
    HttpJsonClient,
    ScrapeCandidate,
    ScrapeQuery,
    int_from_value,
    music_confidence,
    year_from_date,
)


class ItunesScraper:
    name = "itunes"

    def __init__(
        self,
        source: ScraperSourceConfig,
        *,
        timeout: float,
        language: str = "en-US",
    ) -> None:
        self.source = source
        self.client = HttpJsonClient(timeout)
        self.language = language

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        if query.media_type not in {"album", "track"}:
            return []
        term = " ".join(part for part in (query.artist, query.album, query.title) if part)
        data = self.client.get(
            self.source.base_url,
            {
                "term": term,
                "media": "music",
                "entity": "album" if query.media_type == "album" else "song",
                "limit": limit,
                "country": _itunes_country(self.language),
                "lang": self.language,
            },
        )
        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            return []
        candidates: list[ScrapeCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = str(
                item.get("collectionName" if query.media_type == "album" else "trackName") or ""
            )
            artist = str(item.get("artistName") or "")
            album = str(item.get("collectionName") or "")
            year = year_from_date(str(item.get("releaseDate") or ""))
            source_id = item.get("collectionId" if query.media_type == "album" else "trackId")
            if not source_id:
                continue
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(source_id),
                    media_type=query.media_type,
                    title=title,
                    artist=artist,
                    album_artist=artist,
                    album=album,
                    year=year,
                    poster_url=_high_res_itunes_artwork(str(item.get("artworkUrl100") or "")),
                    genres=[str(item.get("primaryGenreName"))]
                    if item.get("primaryGenreName")
                    else [],
                    confidence=music_confidence(query, title=title, artist=artist, album=album),
                    external_ids={
                        ("itunes_album" if query.media_type == "album" else "itunes_track"): str(
                            source_id
                        ),
                        **(
                            {"itunes_artist": str(item["artistId"])} if item.get("artistId") else {}
                        ),
                        **(
                            {"itunes_album_artist": str(item["artistId"])}
                            if query.media_type == "album" and item.get("artistId")
                            else {}
                        ),
                    },
                    title_variants=localized_variants(title, language=self.language),
                    artist_variants=localized_variants(artist, language=self.language),
                    album_artist_variants=localized_variants(
                        artist,
                        language=self.language,
                    ),
                    album_variants=localized_variants(album, language=self.language),
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
            self.source.base_url.replace("/search", "/lookup"),
            {"id": candidate.source_id, "entity": "song", "limit": 200},
        )
        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            return []
        tracks = [
            item
            for item in raw_results
            if isinstance(item, dict)
            and item.get("wrapperType") == "track"
            and item.get("kind") == "song"
        ]
        tracks.sort(
            key=lambda item: (
                int_from_value(item.get("discNumber")) or 1,
                int_from_value(item.get("trackNumber")) or 9999,
            )
        )
        return [
            _itunes_track_candidate(candidate, item, index)
            for index, item in enumerate(tracks, start=1)
            if item.get("trackName")
        ][: expected_count or None]


class NeteaseScraper:
    name = "netease"

    def __init__(self, source: ScraperSourceConfig, *, timeout: float) -> None:
        self.source = source
        self.timeout = timeout

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        songs = self._search_songs(query, limit=limit * 3)
        if query.media_type == "album":
            return self._album_candidates(query, songs, limit)
        if query.media_type == "track":
            return self._track_candidates(query, songs, limit)
        return []

    def _search_songs(self, query: ScrapeQuery, *, limit: int) -> list[dict[str, Any]]:
        term = " ".join(part for part in (query.artist, query.album, query.title) if part)
        if not term:
            return []
        data = self._request_json(
            self.source.base_url,
            data={
                "s": term,
                "type": "1",
                "limit": limit,
                "offset": 0,
            },
        )
        songs = data.get("result", {}).get("songs", [])
        return [song for song in songs if isinstance(song, dict)] if isinstance(songs, list) else []

    def _album_candidates(
        self, query: ScrapeQuery, songs: list[dict[str, Any]], limit: int
    ) -> list[ScrapeCandidate]:
        by_album: dict[str, ScrapeCandidate] = {}
        for song in songs:
            album = song.get("album")
            if not isinstance(album, dict) or not album.get("id"):
                continue
            title = str(album.get("name") or "")
            artist = canonicalize_music_artist(_netease_artist(song)) or _netease_artist(song)
            candidate = ScrapeCandidate(
                source=self.name,
                source_id=str(album["id"]),
                media_type="album",
                title=title,
                artist=artist,
                album_artist=artist,
                album=title,
                year=_year_from_millis(album.get("publishTime")),
                poster_url=_netease_picture_url(album.get("picId")),
                confidence=music_confidence(query, title=title, artist=artist, album=title),
                external_ids={
                    "netease_album": str(album["id"]),
                    **(
                        {"netease_artist": artist_id}
                        if (artist_id := _netease_artist_id(song))
                        else {}
                    ),
                    **_netease_artist_credit_ids(song, album_artist=True),
                },
                title_variants=localized_variants(title, language="zh-CN"),
                artist_variants=localized_variants(artist, language="zh-CN"),
                album_artist_variants=localized_variants(
                    artist,
                    language="zh-CN",
                ),
                album_variants=localized_variants(title, language="zh-CN"),
            )
            current = by_album.get(candidate.source_id)
            if current is None or candidate.confidence > current.confidence:
                by_album[candidate.source_id] = candidate
        return sorted(by_album.values(), key=lambda item: item.confidence, reverse=True)[:limit]

    def _track_candidates(
        self, query: ScrapeQuery, songs: list[dict[str, Any]], limit: int
    ) -> list[ScrapeCandidate]:
        candidates: list[ScrapeCandidate] = []
        for song in songs[:limit]:
            album = song.get("album")
            album_name = str(album.get("name") or "") if isinstance(album, dict) else ""
            title = str(song.get("name") or "")
            artist = canonicalize_music_artist(_netease_artist(song)) or _netease_artist(song)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(song.get("id") or ""),
                    media_type="track",
                    title=title,
                    artist=artist,
                    album_artist=artist,
                    album=album_name,
                    year=_year_from_millis(album.get("publishTime"))
                    if isinstance(album, dict)
                    else None,
                    poster_url=_netease_picture_url(album.get("picId"))
                    if isinstance(album, dict)
                    else "",
                    confidence=music_confidence(
                        query, title=title, artist=artist, album=album_name
                    ),
                    external_ids={
                        "netease_track": str(song.get("id") or ""),
                        **(
                            {"netease_album": str(album["id"])}
                            if isinstance(album, dict) and album.get("id")
                            else {}
                        ),
                        **(
                            {"netease_artist": artist_id}
                            if (artist_id := _netease_artist_id(song))
                            else {}
                        ),
                        **_netease_artist_credit_ids(song),
                    },
                    title_variants=localized_variants(title, language="zh-CN"),
                    artist_variants=localized_variants(artist, language="zh-CN"),
                    album_artist_variants=localized_variants(
                        artist,
                        language="zh-CN",
                    ),
                    album_variants=localized_variants(album_name, language="zh-CN"),
                )
            )
        return candidates

    def album_tracks(
        self,
        candidate: ScrapeCandidate,
        *,
        expected_count: int | None = None,
    ) -> list[ScrapeCandidate]:
        data = self._request_json(_netease_album_url(self.source.base_url, candidate.source_id))
        album = data.get("album", {})
        if not isinstance(album, dict):
            return []
        songs = data.get("songs", [])
        if not isinstance(songs, list):
            return []
        album_name = str(album.get("name") or candidate.album or candidate.title)
        year = _year_from_millis(album.get("publishTime")) or candidate.year
        tracks = [
            _netease_track_candidate(candidate, song, index, album_name, year)
            for index, song in enumerate(songs, start=1)
            if isinstance(song, dict) and song.get("name")
        ]
        return tracks[: expected_count or None]

    def album_by_signature(
        self,
        query: ScrapeQuery,
        durations: list[float],
    ) -> tuple[ScrapeCandidate, list[ScrapeCandidate]] | None:
        if (
            query.media_type != "album"
            or not query.artist
            or not durations
            or any(duration <= 0 for duration in durations)
        ):
            return None
        artist_id = self._artist_id(query.artist)
        if not artist_id:
            return None
        albums = self._artist_albums(artist_id)
        summaries = [
            album for album in albums if int_from_value(album.get("size")) == len(durations)
        ]
        if query.year:
            same_year = [
                album
                for album in summaries
                if _year_from_millis(album.get("publishTime")) == query.year
            ]
            summaries = same_year or summaries

        matches: list[tuple[float, float, dict[str, Any]]] = []
        for summary in summaries:
            album_id = str(summary.get("id") or "")
            if not album_id:
                continue
            data = self._request_json(_netease_album_url(self.source.base_url, album_id))
            songs = data.get("songs")
            if not isinstance(songs, list) or len(songs) != len(durations):
                continue
            remote_durations = [
                float(song.get("dt") or 0) / 1000 for song in songs if isinstance(song, dict)
            ]
            if len(remote_durations) != len(durations) or any(
                duration <= 0 for duration in remote_durations
            ):
                continue
            differences = [
                abs(local - remote)
                for local, remote in zip(durations, remote_durations, strict=True)
            ]
            within_three = sum(difference <= 3 for difference in differences)
            if (
                within_three < max(1, (len(differences) * 4 + 4) // 5)
                or sum(differences) / len(differences) > 3
                or max(differences) > 15
            ):
                continue
            matches.append(
                (
                    sum(differences) / len(differences),
                    max(differences),
                    data,
                )
            )
        if not matches:
            return None
        matches.sort(key=lambda match: (match[0], match[1]))
        best_mean, _best_max, data = matches[0]
        if len(matches) > 1:
            second_mean, _second_max, second_data = matches[1]
            best_title = str(data.get("album", {}).get("name") or "")
            second_title = str(second_data.get("album", {}).get("name") or "")
            if best_title != second_title and second_mean - best_mean < 0.5:
                return None
        album = data.get("album")
        songs = data.get("songs")
        if not isinstance(album, dict) or not isinstance(songs, list):
            return None
        candidate = _netease_album_candidate(query, album, artist_id)
        tracks = [
            _netease_track_candidate(
                candidate,
                song,
                index,
                candidate.title,
                candidate.year,
            )
            for index, song in enumerate(songs, start=1)
            if isinstance(song, dict) and song.get("name")
        ]
        return (candidate, tracks) if len(tracks) == len(durations) else None

    def _artist_id(self, artist: str) -> str:
        data = self._request_json(
            self.source.base_url,
            data={
                "s": artist,
                "type": "100",
                "limit": 10,
                "offset": 0,
            },
        )
        rows = data.get("result", {}).get("artists", [])
        if not isinstance(rows, list):
            return ""
        canonical = canonicalize_music_artist(artist)
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            names = [str(row.get("name") or "")]
            aliases = row.get("alias")
            if isinstance(aliases, list):
                names.extend(str(alias) for alias in aliases)
            if any(canonicalize_music_artist(name) == canonical for name in names):
                return str(row["id"])
        return ""

    def _artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        url = _netease_artist_albums_url(self.source.base_url, artist_id)
        albums: list[dict[str, Any]] = []
        offset = 0
        while True:
            data = self._request_json(
                url,
                params={"offset": offset, "limit": 200},
            )
            rows = data.get("hotAlbums", [])
            if not isinstance(rows, list):
                return albums
            albums.extend(row for row in rows if isinstance(row, dict))
            if not data.get("more") or not rows:
                return albums
            offset += len(rows)

    def _request_json(
        self,
        url: str,
        *,
        data: dict[str, object] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode() if data else None,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}


class QqMusicScraper:
    name = "qqmusic"

    def __init__(self, source: ScraperSourceConfig, *, timeout: float) -> None:
        self.source = source
        self.timeout = timeout

    def search(self, query: ScrapeQuery, *, limit: int = 5) -> list[ScrapeCandidate]:
        songs = self._search_songs(query, limit=limit * 3)
        if query.media_type == "album":
            return self._album_candidates(query, songs, limit)
        if query.media_type == "track":
            return self._track_candidates(query, songs, limit)
        return []

    def _search_songs(self, query: ScrapeQuery, *, limit: int) -> list[dict[str, Any]]:
        term = " ".join(part for part in (query.artist, query.album, query.title) if part)
        if not term:
            return []
        params = {
            "w": term,
            "format": "json",
            "p": 1,
            "n": limit,
            "cr": 1,
            "new_json": 1,
        }
        url = f"{self.source.base_url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return []
        songs = data.get("data", {}).get("song", {}).get("list", [])
        return [song for song in songs if isinstance(song, dict)] if isinstance(songs, list) else []

    def _album_candidates(
        self, query: ScrapeQuery, songs: list[dict[str, Any]], limit: int
    ) -> list[ScrapeCandidate]:
        by_album: dict[str, ScrapeCandidate] = {}
        for song in songs:
            album = song.get("album")
            if not isinstance(album, dict) or not album.get("mid"):
                continue
            title = str(album.get("title") or album.get("name") or "")
            artist = _qq_artist(song)
            candidate = ScrapeCandidate(
                source=self.name,
                source_id=str(album["mid"]),
                media_type="album",
                title=title,
                artist=artist,
                album=title,
                poster_url=_qq_album_art(album.get("pmid") or album.get("mid")),
                confidence=music_confidence(query, title=title, artist=artist, album=title),
                external_ids={
                    "qqmusic_album": str(album["mid"]),
                    **({"qqmusic_artist": artist_id} if (artist_id := _qq_artist_id(song)) else {}),
                    **_qq_artist_credit_ids(song, album_artist=True),
                },
                title_variants=localized_variants(title, language="zh-CN"),
                artist_variants=localized_variants(artist, language="zh-CN"),
                album_artist_variants=localized_variants(
                    artist,
                    language="zh-CN",
                ),
                album_variants=localized_variants(title, language="zh-CN"),
            )
            current = by_album.get(candidate.source_id)
            if current is None or candidate.confidence > current.confidence:
                by_album[candidate.source_id] = candidate
        return sorted(by_album.values(), key=lambda item: item.confidence, reverse=True)[:limit]

    def _track_candidates(
        self, query: ScrapeQuery, songs: list[dict[str, Any]], limit: int
    ) -> list[ScrapeCandidate]:
        candidates: list[ScrapeCandidate] = []
        for song in songs[:limit]:
            album = song.get("album")
            album_name = (
                str(album.get("title") or album.get("name") or "")
                if isinstance(album, dict)
                else ""
            )
            title = str(song.get("title") or song.get("name") or "")
            artist = _qq_artist(song)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(song.get("mid") or song.get("id") or ""),
                    media_type="track",
                    title=title,
                    artist=artist,
                    album_artist=artist,
                    album=album_name,
                    poster_url=_qq_album_art(album.get("pmid") or album.get("mid"))
                    if isinstance(album, dict)
                    else "",
                    confidence=music_confidence(
                        query, title=title, artist=artist, album=album_name
                    ),
                    external_ids={
                        "qqmusic_track": str(song.get("mid") or song.get("id") or ""),
                        **(
                            {"qqmusic_album": str(album["mid"])}
                            if isinstance(album, dict) and album.get("mid")
                            else {}
                        ),
                        **(
                            {"qqmusic_artist": artist_id}
                            if (artist_id := _qq_artist_id(song))
                            else {}
                        ),
                        **_qq_artist_credit_ids(song),
                    },
                    title_variants=localized_variants(title, language="zh-CN"),
                    artist_variants=localized_variants(artist, language="zh-CN"),
                    album_artist_variants=localized_variants(
                        artist,
                        language="zh-CN",
                    ),
                    album_variants=localized_variants(album_name, language="zh-CN"),
                )
            )
        return candidates

    def album_tracks(
        self,
        candidate: ScrapeCandidate,
        *,
        expected_count: int | None = None,
    ) -> list[ScrapeCandidate]:
        params = {
            "albummid": candidate.source_id,
            "format": "json",
            "platform": "yqq",
            "inCharset": "utf8",
            "outCharset": "utf-8",
        }
        url = f"https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return []
        album = data.get("data", {})
        songs = album.get("list", []) if isinstance(album, dict) else []
        if not isinstance(songs, list):
            return []
        album_name = str(album.get("name") or candidate.album or candidate.title)
        tracks = [
            _qq_track_candidate(candidate, song, index, album_name)
            for index, song in enumerate(songs, start=1)
            if isinstance(song, dict) and (song.get("songname") or song.get("songorig"))
        ]
        return tracks[: expected_count or None]


def _itunes_track_candidate(
    candidate: ScrapeCandidate, item: dict[str, Any], index: int
) -> ScrapeCandidate:
    return ScrapeCandidate(
        source="itunes",
        source_id=str(item.get("trackId") or f"{candidate.source_id}:{index}"),
        media_type="track",
        title=str(item.get("trackName") or ""),
        artist=str(item.get("artistName") or candidate.artist),
        album_artist=candidate.album_artist or candidate.artist,
        album=str(item.get("collectionName") or candidate.album or candidate.title),
        year=year_from_date(str(item.get("releaseDate") or "")) or candidate.year,
        disc=int_from_value(item.get("discNumber")),
        track=int_from_value(item.get("trackNumber")) or index,
        poster_url=_high_res_itunes_artwork(str(item.get("artworkUrl100") or ""))
        or candidate.poster_url,
        genres=[str(item.get("primaryGenreName"))]
        if item.get("primaryGenreName")
        else candidate.genres,
        confidence=1,
        external_ids={
            **candidate.external_ids,
            "itunes_track": str(item.get("trackId") or f"{candidate.source_id}:{index}"),
            **({"itunes_artist": str(item["artistId"])} if item.get("artistId") else {}),
        },
        title_variants=localized_variants(
            str(item.get("trackName") or ""),
            language=next(iter(candidate.title_variants), "und"),
        ),
        artist_variants=localized_variants(
            str(item.get("artistName") or candidate.artist),
            language=next(iter(candidate.artist_variants), "und"),
        ),
        album_artist_variants=candidate.album_artist_variants or candidate.artist_variants,
        album_variants=candidate.album_variants or candidate.title_variants,
    )


def _netease_track_candidate(
    candidate: ScrapeCandidate, song: dict[str, Any], index: int, album_name: str, year: int | None
) -> ScrapeCandidate:
    artist = canonicalize_music_artist(_netease_artist(song)) or (
        _netease_artist(song) or candidate.artist
    )
    return ScrapeCandidate(
        source="netease",
        source_id=str(song.get("id") or f"{candidate.source_id}:{index}"),
        media_type="track",
        title=str(song.get("name") or ""),
        artist=artist,
        album_artist=candidate.album_artist or candidate.artist,
        album=album_name,
        year=year,
        disc=_netease_disc(song.get("cd")),
        track=int_from_value(song.get("no")) or index,
        poster_url=candidate.poster_url,
        genres=candidate.genres,
        styles=candidate.styles,
        tags=candidate.tags,
        composers=candidate.composers,
        confidence=1,
        external_ids={
            **candidate.external_ids,
            "netease_track": str(song.get("id") or f"{candidate.source_id}:{index}"),
            **({"netease_artist": artist_id} if (artist_id := _netease_artist_id(song)) else {}),
            **_netease_artist_credit_ids(song),
        },
        title_variants=localized_variants(
            str(song.get("name") or ""),
            language="zh-CN",
        ),
        artist_variants=localized_variants(
            artist,
            language="zh-CN",
        ),
        album_artist_variants=candidate.album_artist_variants or candidate.artist_variants,
        album_variants=localized_variants(album_name, language="zh-CN"),
    )


def _netease_album_candidate(
    query: ScrapeQuery,
    album: dict[str, Any],
    artist_id: str,
) -> ScrapeCandidate:
    title = str(album.get("name") or "")
    artist_data = album.get("artist")
    artist_name = (
        str(artist_data.get("name") or "")
        if isinstance(artist_data, dict)
        else str(query.artist or "")
    )
    artist = canonicalize_music_artist(artist_name) or artist_name
    album_id = str(album.get("id") or "")
    artist_variants = localized_variants(artist, language="zh-CN")
    title_variants = localized_variants(title, language="zh-CN")
    poster_url = str(album.get("picUrl") or "") or _netease_picture_url(album.get("picId"))
    return ScrapeCandidate(
        source="netease",
        source_id=album_id,
        media_type="album",
        title=title,
        artist=artist,
        album_artist=artist,
        album=title,
        year=_year_from_millis(album.get("publishTime")) or query.year,
        poster_url=poster_url,
        confidence=1,
        external_ids={
            "netease_album": album_id,
            "netease_artist": artist_id,
            "netease_artist_credit": artist_id,
            "netease_album_artist_credit": artist_id,
        },
        title_variants=title_variants,
        artist_variants=artist_variants,
        album_artist_variants=artist_variants,
        album_variants=title_variants,
    )


def _qq_track_candidate(
    candidate: ScrapeCandidate, song: dict[str, Any], index: int, album_name: str
) -> ScrapeCandidate:
    return ScrapeCandidate(
        source="qqmusic",
        source_id=str(
            song.get("songmid") or song.get("songid") or f"{candidate.source_id}:{index}"
        ),
        media_type="track",
        title=str(song.get("songname") or song.get("songorig") or ""),
        artist=_qq_artist(song) or candidate.artist,
        album_artist=candidate.album_artist or candidate.artist,
        album=album_name,
        year=candidate.year,
        disc=1,
        track=index,
        poster_url=candidate.poster_url,
        genres=candidate.genres,
        styles=candidate.styles,
        tags=candidate.tags,
        composers=candidate.composers,
        confidence=1,
        external_ids={
            **candidate.external_ids,
            "qqmusic_track": str(
                song.get("songmid") or song.get("songid") or f"{candidate.source_id}:{index}"
            ),
            **({"qqmusic_artist": artist_id} if (artist_id := _qq_artist_id(song)) else {}),
            **_qq_artist_credit_ids(song),
        },
        title_variants=localized_variants(
            str(song.get("songname") or song.get("songorig") or ""),
            language="zh-CN",
        ),
        artist_variants=localized_variants(
            _qq_artist(song) or candidate.artist,
            language="zh-CN",
        ),
        album_artist_variants=candidate.album_artist_variants or candidate.artist_variants,
        album_variants=localized_variants(album_name, language="zh-CN"),
    )


def _netease_artist(song: dict[str, Any]) -> str:
    artists = song.get("artists") or song.get("ar")
    if not isinstance(artists, list):
        return ""
    return ", ".join(
        str(item.get("name")) for item in artists if isinstance(item, dict) and item.get("name")
    )


def _netease_artist_id(song: dict[str, Any]) -> str:
    artists = song.get("artists") or song.get("ar")
    if not isinstance(artists, list):
        return ""
    for artist in artists:
        if isinstance(artist, dict) and artist.get("id"):
            return str(artist["id"])
    return ""


def _netease_artist_credit_ids(
    song: dict[str, Any],
    *,
    album_artist: bool = False,
) -> dict[str, str]:
    artists = song.get("artists") or song.get("ar")
    if not isinstance(artists, list):
        return {}
    ids = [str(artist["id"]) for artist in artists if isinstance(artist, dict) and artist.get("id")]
    if not ids:
        return {}
    key = "netease_album_artist_credit" if album_artist else "netease_artist_credit"
    return {key: "+".join(ids)}


def _qq_artist(song: dict[str, Any]) -> str:
    singers = song.get("singer")
    if not isinstance(singers, list):
        return ""
    return ", ".join(
        str(item.get("name")) for item in singers if isinstance(item, dict) and item.get("name")
    )


def _qq_artist_id(song: dict[str, Any]) -> str:
    singers = song.get("singer")
    if not isinstance(singers, list):
        return ""
    for singer in singers:
        if isinstance(singer, dict) and (singer.get("mid") or singer.get("id")):
            return str(singer.get("mid") or singer.get("id"))
    return ""


def _qq_artist_credit_ids(
    song: dict[str, Any],
    *,
    album_artist: bool = False,
) -> dict[str, str]:
    singers = song.get("singer")
    if not isinstance(singers, list):
        return {}
    ids = [
        str(singer.get("mid") or singer.get("id"))
        for singer in singers
        if isinstance(singer, dict) and (singer.get("mid") or singer.get("id"))
    ]
    if not ids:
        return {}
    key = "qqmusic_album_artist_credit" if album_artist else "qqmusic_artist_credit"
    return {key: "+".join(ids)}


def _itunes_country(language: str) -> str:
    region = language.replace("_", "-").split("-")[-1].upper()
    return region if len(region) == 2 else "US"


def _year_from_millis(value: object) -> int | None:
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return year_from_date(dt.datetime.fromtimestamp(number / 1000).date().isoformat())


def _netease_picture_url(pic_id: object) -> str:
    return f"https://p3.music.126.net/{pic_id}.jpg" if pic_id else ""


def _qq_album_art(album_mid: object) -> str:
    if not album_mid:
        return ""
    return f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{album_mid}.jpg"


def _netease_album_url(search_url: str, album_id: str) -> str:
    parsed = urllib.parse.urlparse(search_url)
    base = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme and parsed.netloc
        else "https://music.163.com"
    )
    return f"{base}/api/v1/album/{urllib.parse.quote(album_id)}"


def _netease_artist_albums_url(search_url: str, artist_id: str) -> str:
    parsed = urllib.parse.urlparse(search_url)
    base = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme and parsed.netloc
        else "https://music.163.com"
    )
    return f"{base}/api/artist/albums/{urllib.parse.quote(artist_id)}"


def _netease_disc(value: object) -> int:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return int(digits) if digits else 1


def _high_res_itunes_artwork(url: str) -> str:
    return url.replace("100x100bb", "600x600bb") if url else ""
