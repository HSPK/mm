"""Metadata merge policy for organizer scrape workflows."""

from __future__ import annotations

from dataclasses import replace

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate


def external_track_nfo_candidate(candidate: ScrapeCandidate | None) -> ScrapeCandidate | None:
    if candidate and candidate.media_type == "track":
        return candidate
    return None


def lyrics_query_candidate(
    album_candidate: ScrapeCandidate | None,
    track: ParsedMediaFile,
) -> ScrapeCandidate | None:
    if album_candidate is None:
        return None
    return replace(
        album_candidate,
        media_type="track",
        title=track.title,
        artist=track.artist or album_candidate.artist,
        album=album_candidate.album or album_candidate.title or track.album,
        year=album_candidate.year or track.year,
        lyrics="",
        synced_lyrics="",
    )
