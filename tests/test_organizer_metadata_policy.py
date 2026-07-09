from __future__ import annotations

from pathlib import Path

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.metadata_policy import external_track_nfo_candidate, lyrics_query_candidate
from mm.organizer.scrapers import ScrapeCandidate


def test_album_candidate_is_not_track_nfo_candidate():
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="album-1",
        media_type="album",
        title="Album",
    )

    assert external_track_nfo_candidate(candidate) is None


def test_album_candidate_can_seed_track_lyrics_query():
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="album-1",
        media_type="album",
        title="Album",
        artist="Artist",
        album="Album",
        year=2024,
    )
    track = ParsedMediaFile(
        path=Path("01 - Song.flac"),
        media_type="track",
        title="Song",
        artist="Artist",
        album="Album",
        track=1,
    )

    query_candidate = lyrics_query_candidate(candidate, track)

    assert query_candidate is not None
    assert query_candidate.media_type == "track"
    assert query_candidate.title == "Song"
    assert query_candidate.album == "Album"
