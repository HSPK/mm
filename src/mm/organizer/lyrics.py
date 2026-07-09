"""Lyrics provider adapters used by organizer scraping."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def lyrics_from_source(source: str, track: str, artist: str, album: str) -> dict[str, Any] | None:
    if source == "all":
        for name in ("lrclib", "netease", "qq"):
            result = lyrics_from_source(name, track, artist, album)
            if result:
                return result
        return None
    if source == "netease":
        return _first_lyrics_result(search_netease_lyrics(track, artist, album, limit=3))
    if source == "qq":
        return _first_lyrics_result(search_qq_lyrics(track, artist, album, limit=3))
    return _lrclib_lyrics(track=track, artist=artist, album=album)


def get_lrclib_lyrics(track: str, artist: str = "", album: str = "") -> dict[str, Any] | None:
    return _lrclib_lyrics(track, artist, album)


def search_lrclib_lyrics(
    track: str,
    artist: str = "",
    album: str = "",
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not track:
        return []
    params = {"track_name": track, "artist_name": artist, "album_name": album}
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value})
    request = urllib.request.Request(
        f"https://lrclib.net/api/search?{query}",
        headers={"User-Agent": "litemm/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data[:limit] if isinstance(item, dict)]


def search_netease_lyrics(
    track: str,
    artist: str = "",
    album: str = "",
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    term = " ".join(part for part in (track, artist, album) if part).strip()
    if not term:
        return []
    request = urllib.request.Request(
        "https://music.163.com/api/search/get/web?csrf_token=",
        data=urllib.parse.urlencode({
            "s": term,
            "type": "1",
            "limit": limit,
            "offset": 0,
        }).encode(),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://music.163.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return []
    songs = data.get("result", {}).get("songs", [])
    if not isinstance(songs, list):
        return []
    return [_netease_lyrics_result(song) for song in songs[:limit] if isinstance(song, dict)]


def search_qq_lyrics(
    track: str,
    artist: str = "",
    album: str = "",
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    term = " ".join(part for part in (track, artist, album) if part).strip()
    if not term:
        return []
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp?" + urllib.parse.urlencode({
        "w": term,
        "format": "json",
        "p": 1,
        "n": limit,
        "cr": 1,
        "new_json": 1,
    })
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return []
    songs = data.get("data", {}).get("song", {}).get("list", [])
    if not isinstance(songs, list):
        return []
    return [_qq_lyrics_result(song) for song in songs[:limit] if isinstance(song, dict)]


def _lrclib_lyrics(track: str, artist: str = "", album: str = "") -> dict[str, Any] | None:
    if not track:
        return None
    params = {"track_name": track, "artist_name": artist, "album_name": album}
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value})
    request = urllib.request.Request(
        f"https://lrclib.net/api/get?{query}",
        headers={"User-Agent": "litemm/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _netease_lyrics_result(song: dict[str, Any]) -> dict[str, Any]:
    if not song.get("id"):
        return {}
    lyric = _netease_lyric(str(song["id"]))
    if not lyric:
        return {}
    artists = song.get("artists")
    artist_name = ", ".join(
        str(item.get("name"))
        for item in artists
        if isinstance(item, dict) and item.get("name")
    ) if isinstance(artists, list) else ""
    album_item = song.get("album")
    album_name = str(album_item.get("name") or "") if isinstance(album_item, dict) else ""
    return {
        "source": "netease",
        "id": str(song["id"]),
        "trackName": str(song.get("name") or ""),
        "artistName": artist_name,
        "albumName": album_name,
        "duration": _duration_seconds(song.get("duration")),
        "plainLyrics": "",
        "syncedLyrics": lyric,
    }


def _qq_lyrics_result(song: dict[str, Any]) -> dict[str, Any]:
    if not song.get("mid"):
        return {}
    lyric = _qq_lyric(str(song["mid"]))
    if not lyric:
        return {}
    singers = song.get("singer")
    artist_name = ", ".join(
        str(item.get("name"))
        for item in singers
        if isinstance(item, dict) and item.get("name")
    ) if isinstance(singers, list) else ""
    album_item = song.get("album")
    album_name = (
        str(album_item.get("title") or album_item.get("name") or "")
        if isinstance(album_item, dict)
        else ""
    )
    return {
        "source": "qq",
        "id": str(song["mid"]),
        "trackName": str(song.get("title") or song.get("name") or ""),
        "artistName": artist_name,
        "albumName": album_name,
        "duration": _duration_seconds(song.get("interval")),
        "plainLyrics": "",
        "syncedLyrics": lyric,
    }


def _netease_lyric(song_id: str) -> str:
    url = "https://music.163.com/api/song/lyric?" + urllib.parse.urlencode({
        "id": song_id,
        "lv": 1,
        "kv": 1,
        "tv": -1,
    })
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return ""
    lyric = data.get("lrc", {}).get("lyric", "")
    return str(lyric or "")


def _qq_lyric(song_mid: str) -> str:
    url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?" + urllib.parse.urlencode({
        "songmid": song_mid,
        "format": "json",
        "nobase64": 1,
        "g_tk": 5381,
    })
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://y.qq.com/",
            "Origin": "https://y.qq.com",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return ""
    return str(data.get("lyric") or "")


def _first_lyrics_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in results:
        if item.get("plainLyrics") or item.get("syncedLyrics"):
            return item
    return None


def _duration_seconds(value: object) -> float | None:
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    return number / 1000 if number > 10_000 else number
