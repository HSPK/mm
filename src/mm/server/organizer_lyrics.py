from __future__ import annotations

import re
from hashlib import blake2b
from pathlib import Path

from fastapi import HTTPException

from mm.config import AUDIO_EXTENSIONS
from mm.organizer.lyrics import (
    get_lrclib_lyrics,
    search_kugou_lyrics,
    search_lrclib_lyrics,
    search_netease_lyrics,
    search_qq_lyrics,
)
from mm.server.organizer_paths import allowed_media_source_path
from mm.server.organizer_schemas import OrganizerLyricsCandidate


def safe_audio_path(path: str) -> Path:
    media_path = Path(path).expanduser().resolve()
    if not media_path.is_file():
        raise HTTPException(404, "Audio file not found")
    if media_path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio file")
    if not allowed_media_source_path(media_path):
        raise HTTPException(403, "Audio file is outside configured media sources")
    return media_path


def local_lyrics_resource(path: Path) -> tuple[str, str, str]:
    plain = ""
    synced = ""
    version = blake2b(digest_size=16)
    for candidate, synced_lyrics in (
        (path.with_suffix(".lyrics.txt"), False),
        (path.with_suffix(".lyric.txt"), False),
        (path.with_suffix(".lrc"), True),
    ):
        if not candidate.is_file():
            continue
        try:
            content = candidate.read_text(encoding="utf-8")
            stat = candidate.stat()
        except OSError:
            continue
        version.update(candidate.name.encode("utf-8"))
        version.update(str(stat.st_mtime_ns).encode("ascii"))
        version.update(content.encode("utf-8"))
        if synced_lyrics:
            synced = content
        elif not plain:
            plain = content
    return plain, synced, version.hexdigest() if plain or synced else ""


def search_lyrics_source(
    source: str,
    title: str,
    artist: str,
    album: str,
    *,
    limit: int,
) -> list[dict[str, object]]:
    if source == "all":
        results: list[dict[str, object]] = []
        for name in ("lrclib", "netease", "kugou", "qq"):
            results.extend(search_lyrics_source(name, title, artist, album, limit=limit))
        return results[:limit]
    if source == "netease":
        return search_netease_lyrics(title, artist, album, limit=limit)
    if source == "kugou":
        return search_kugou_lyrics(title, artist, album, limit=limit)
    if source == "qq":
        return search_qq_lyrics(title, artist, album, limit=limit)
    raw = search_lrclib_lyrics(title, artist, album, limit=limit)
    exact = get_lrclib_lyrics(title, artist, album)
    if exact:
        raw = [exact, *raw]
    return raw


def lyrics_candidate(
    item: dict[str, object],
    query_title: str,
    query_artist: str,
    query_album: str,
) -> OrganizerLyricsCandidate:
    title = str(item.get("trackName") or "")
    artist = str(item.get("artistName") or "")
    album = str(item.get("albumName") or "")
    return OrganizerLyricsCandidate(
        source=str(item.get("source") or "lrclib"),
        source_id=str(item.get("id") or f"{title}:{artist}:{album}"),
        title=title,
        artist=artist,
        album=album,
        duration=_float_or_none(item.get("duration")),
        lyrics=str(item.get("plainLyrics") or ""),
        synced_lyrics=str(item.get("syncedLyrics") or ""),
        confidence=_music_lyrics_confidence(
            query_title,
            query_artist,
            query_album,
            title,
            artist,
            album,
        ),
    )


def _music_lyrics_confidence(
    query_title: str,
    query_artist: str,
    query_album: str,
    title: str,
    artist: str,
    album: str,
) -> float:
    scores = [
        0.6 * _text_similarity(query_title, title),
        0.3 * _text_similarity(query_artist, artist),
        0.1 * _text_similarity(query_album, album),
    ]
    return round(sum(scores), 3)


def _text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return 1.0 if _normalized_title(left) == _normalized_title(right) else 0.0


def _normalized_title(value: str) -> str:
    return re.sub(r"[_\W]+", " ", value.lower()).strip()


def _float_or_none(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
