from __future__ import annotations

from pathlib import Path
from typing import Protocol

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate, ScrapeQuery, search_all
from mm.server.organizer_schemas import OrganizerCandidate, OrganizerItem


class CandidateSelectionBody(Protocol):
    source: str | None
    selected_candidates: dict[str, OrganizerCandidate]


def parsed_from_item(item: OrganizerItem) -> ParsedMediaFile:
    return ParsedMediaFile(
        path=Path(item.path),
        media_type=item.media_type,
        title=item.title,
        artist=item.artist,
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
    return OrganizerCandidate(**candidate.__dict__)


def candidate_from_body(candidate: OrganizerCandidate | None) -> ScrapeCandidate | None:
    return ScrapeCandidate(**candidate.model_dump()) if candidate else None


def selected_candidate(
    body: CandidateSelectionBody,
    item: OrganizerItem,
) -> ScrapeCandidate | None:
    candidate = body.selected_candidates.get(item.path)
    return candidate_from_body(candidate) if candidate else None


def best_match(item: ParsedMediaFile, source: str | None) -> ScrapeCandidate | None:
    candidates = search_all(query_from_parsed(item), source=source, limit=1)
    return candidates[0] if candidates else None
