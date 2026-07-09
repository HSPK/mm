"""Music platform scraper adapters for iTunes, NetEase, and QQ Music."""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mm.config import ScraperSourceConfig
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

    def __init__(self, source: ScraperSourceConfig, *, timeout: float) -> None:
        self.source = source
        self.client = HttpJsonClient(timeout)

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
                    album=album,
                    year=year,
                    poster_url=_high_res_itunes_artwork(str(item.get("artworkUrl100") or "")),
                    genres=[str(item.get("primaryGenreName"))]
                    if item.get("primaryGenreName")
                    else [],
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
        request = urllib.request.Request(
            self.source.base_url,
            data=urllib.parse.urlencode(
                {
                    "s": term,
                    "type": "1",
                    "limit": limit,
                    "offset": 0,
                }
            ).encode(),
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return []
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
            artist = _netease_artist(song)
            candidate = ScrapeCandidate(
                source=self.name,
                source_id=str(album["id"]),
                media_type="album",
                title=title,
                artist=artist,
                album=title,
                year=_year_from_millis(album.get("publishTime")),
                poster_url=_netease_picture_url(album.get("picId")),
                confidence=music_confidence(query, title=title, artist=artist, album=title),
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
            artist = _netease_artist(song)
            candidates.append(
                ScrapeCandidate(
                    source=self.name,
                    source_id=str(song.get("id") or ""),
                    media_type="track",
                    title=title,
                    artist=artist,
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
                )
            )
        return candidates

    def album_tracks(
        self,
        candidate: ScrapeCandidate,
        *,
        expected_count: int | None = None,
    ) -> list[ScrapeCandidate]:
        request = urllib.request.Request(
            _netease_album_url(self.source.base_url, candidate.source_id),
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
            return []
        album = data.get("album", {})
        if not isinstance(album, dict):
            return []
        songs = album.get("songs", [])
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
                    album=album_name,
                    poster_url=_qq_album_art(album.get("pmid") or album.get("mid"))
                    if isinstance(album, dict)
                    else "",
                    confidence=music_confidence(
                        query, title=title, artist=artist, album=album_name
                    ),
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
    )


def _netease_track_candidate(
    candidate: ScrapeCandidate, song: dict[str, Any], index: int, album_name: str, year: int | None
) -> ScrapeCandidate:
    return ScrapeCandidate(
        source="netease",
        source_id=str(song.get("id") or f"{candidate.source_id}:{index}"),
        media_type="track",
        title=str(song.get("name") or ""),
        artist=_netease_artist(song) or candidate.artist,
        album=album_name,
        year=year,
        disc=1,
        track=index,
        poster_url=candidate.poster_url,
        genres=candidate.genres,
        styles=candidate.styles,
        tags=candidate.tags,
        composers=candidate.composers,
        confidence=1,
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
    )


def _netease_artist(song: dict[str, Any]) -> str:
    artists = song.get("artists")
    if not isinstance(artists, list):
        return ""
    return ", ".join(
        str(item.get("name")) for item in artists if isinstance(item, dict) and item.get("name")
    )


def _qq_artist(song: dict[str, Any]) -> str:
    singers = song.get("singer")
    if not isinstance(singers, list):
        return ""
    return ", ".join(
        str(item.get("name")) for item in singers if isinstance(item, dict) and item.get("name")
    )


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
    return f"{base}/api/album/{urllib.parse.quote(album_id)}"


def _high_res_itunes_artwork(url: str) -> str:
    return url.replace("100x100bb", "600x600bb") if url else ""
