from __future__ import annotations

from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Protocol

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate, ScrapeQuery, search_all
from mm.server.organizer_schemas import OrganizerCandidate, OrganizerItem

# Auto-matches below this confidence are discarded rather than written, so a
# weak online hit can't clobber the filename-parsed metadata.
_MIN_AUTO_CONFIDENCE = 0.45

# OrganizerCandidate (API) and ScrapeCandidate (core) are a 1:1 contract; this
# tuple drives the conversion and is asserted for parity in the test suite.
_CANDIDATE_FIELDS = tuple(field.name for field in dataclass_fields(ScrapeCandidate))


class CandidateSelectionBody(Protocol):
    source: str | None
    selected_candidates: dict[str, OrganizerCandidate]


def parsed_from_item(item: OrganizerItem) -> ParsedMediaFile:
    return ParsedMediaFile(
        path=Path(item.path),
        media_type=item.media_type,
        title=item.title,
        artist=item.artist,
        album_artist=item.album_artist,
        album=item.album,
        year=item.year,
        season=item.season,
        episode=item.episode,
        episode_end=item.episode_end,
        disc=item.disc,
        track=item.track,
        parse_template=item.parse_template,
        parse_relative_path=item.parse_relative_path,
        confidence=item.confidence,
        duration=item.duration,
        mime_type=item.mime_type,
    )


def query_from_item(item: OrganizerItem) -> ScrapeQuery:
    return ScrapeQuery(
        media_type=item.media_type,
        title=item.title,
        artist=item.artist,
        album=item.album,
        year=item.year,
        season=item.season,
        episode=item.episode,
        track=item.track,
    )


def query_from_parsed(item: ParsedMediaFile) -> ScrapeQuery:
    return ScrapeQuery(
        media_type=item.media_type,
        title=item.title,
        artist=item.artist,
        album=item.album,
        year=item.year,
        season=item.season,
        episode=item.episode,
        track=item.track,
    )


def candidate_response(candidate: ScrapeCandidate) -> OrganizerCandidate:
    return OrganizerCandidate(**{name: getattr(candidate, name) for name in _CANDIDATE_FIELDS})


def candidate_from_body(candidate: OrganizerCandidate | None) -> ScrapeCandidate | None:
    if candidate is None:
        return None
    data = candidate.model_dump()
    return ScrapeCandidate(**{name: data[name] for name in _CANDIDATE_FIELDS if name in data})


def selected_candidate(
    body: CandidateSelectionBody,
    item: OrganizerItem,
) -> ScrapeCandidate | None:
    key = item.item_uid or item.path
    candidate = body.selected_candidates.get(key)
    if candidate is None and key != item.path:
        candidate = body.selected_candidates.get(item.path)
    return candidate_from_body(candidate) if candidate else None


def best_match(item: ParsedMediaFile, source: str | None) -> ScrapeCandidate | None:
    candidates = search_all(query_from_parsed(item), source=source, limit=1)
    if not candidates:
        return None
    best = candidates[0]
    # Don't silently apply a weak auto-match; leave the filename-parsed data in
    # place so a wrong online hit can't overwrite it. Manual selection bypasses
    # this because it goes through `selected_candidate`, not `best_match`.
    return best if best.confidence >= _MIN_AUTO_CONFIDENCE else None
