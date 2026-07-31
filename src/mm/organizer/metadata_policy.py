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
        album_artist=track.album_artist or album_candidate.album_artist or album_candidate.artist,
        album=album_candidate.album or album_candidate.title or track.album,
        year=album_candidate.year or track.year,
        title_variants={"und": track.title},
        lyrics="",
        synced_lyrics="",
    )


def local_track_candidate(
    album_candidate: ScrapeCandidate | None,
    track: ParsedMediaFile,
) -> ScrapeCandidate | None:
    """Build a track candidate from the filename-parsed data (+ album context).

    Used on an explicit overwrite to reset a stale/mismatched track NFO to the
    correct local title instead of leaving a wrong scraped name in place. Returns
    None when the album itself did not match, preserving the policy of not
    writing local-only NFOs for unscraped albums.
    """
    if album_candidate is None:
        return None
    return replace(
        album_candidate,
        source="local",
        source_id="",
        media_type="track",
        title=track.title,
        artist=track.artist or album_candidate.artist,
        album_artist=track.album_artist or album_candidate.album_artist or album_candidate.artist,
        album=album_candidate.album or album_candidate.title or track.album or "",
        year=track.year or album_candidate.year,
        disc=track.disc,
        track=track.track,
        overview="",
        external_ids={
            key: value
            for key, value in album_candidate.external_ids.items()
            if key.endswith(("artist", "album", "release", "release_group"))
        },
        title_variants={"und": track.title},
        lyrics="",
        synced_lyrics="",
    )
