"""Write organizer scrape outputs with one metadata policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mm.organizer.artwork import ArtworkPlan, download_artwork, plan_artworks
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.metadata_policy import external_track_nfo_candidate
from mm.organizer.nfo import NfoDocument, build_album_nfo, build_nfo, write_nfo
from mm.organizer.scrapers import ScrapeCandidate, enrich_candidate


@dataclass(frozen=True)
class MetadataWriteResult:
    written: int
    targets: list[Path]


def metadata_detail(targets: list[Path]) -> str:
    if not targets:
        return "No missing metadata"
    names = [target.name for target in targets[:3]]
    suffix = f" +{len(targets) - 3}" if len(targets) > 3 else ""
    return ", ".join(names) + suffix


def write_standard_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> MetadataWriteResult:
    if candidate is None:
        return MetadataWriteResult(written=0, targets=[])
    enriched = enrich_candidate(candidate, query=_query_from_parsed(item))
    document = build_nfo(item, enriched)
    targets = _metadata_targets_to_write(item, document, None, enriched, overwrite=overwrite)
    written = 1 if write_nfo_if_needed(document, overwrite=overwrite) else 0
    return MetadataWriteResult(written=written, targets=targets)


def write_album_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    if candidate is None:
        return 0
    return 1 if write_nfo_if_needed(build_album_nfo(item, candidate), overwrite=overwrite) else 0


def write_external_track_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    track_candidate = external_track_nfo_candidate(candidate)
    if not track_candidate:
        return 0
    return 1 if write_nfo_if_needed(build_nfo(item, track_candidate), overwrite=overwrite) else 0


def album_track_metadata_by_path(
    items: list[ParsedMediaFile],
    candidates: list[ScrapeCandidate],
) -> dict[Path, ScrapeCandidate]:
    if not items or not candidates:
        return {}
    result: dict[Path, ScrapeCandidate] = {}
    used_candidates: set[int] = set()
    by_number: dict[tuple[int, int], tuple[int, ScrapeCandidate]] = {}
    for index, candidate in enumerate(candidates):
        if candidate.track is not None:
            by_number[(candidate.disc or 1, candidate.track)] = (index, candidate)

    for item in _sorted_tracks(items):
        if item.track is None:
            continue
        matched = by_number.get((item.disc or 1, item.track))
        if matched is None:
            continue
        candidate_index, candidate = matched
        if candidate_index in used_candidates:
            continue
        result[item.path] = candidate
        used_candidates.add(candidate_index)

    remaining_items = [item for item in _sorted_tracks(items) if item.path not in result]
    remaining_candidates = [
        candidate
        for index, candidate in enumerate(candidates)
        if index not in used_candidates
    ]
    if len(remaining_items) == len(remaining_candidates):
        for item, candidate in zip(remaining_items, remaining_candidates, strict=True):
            result[item.path] = candidate
    return result


def write_track_lyrics(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    return 1 if _write_lyrics(item, candidate, overwrite) else 0


def artwork_plans(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> list[ArtworkPlan]:
    enriched = enrich_candidate(candidate, query=_query_from_parsed(item))
    return plan_artworks(item, enriched, overwrite=overwrite)


def download_ready_artwork(plans: list[ArtworkPlan], *, timeout: float) -> int:
    count = 0
    for plan in plans:
        if plan.status != "ready":
            continue
        download_artwork(plan, timeout=timeout)
        count += 1
    return count


def write_nfo_if_needed(document: NfoDocument, *, overwrite: bool) -> bool:
    if document.target.exists() and not overwrite:
        return False
    write_nfo(document, overwrite=overwrite)
    return True


def _sorted_tracks(items: list[ParsedMediaFile]) -> list[ParsedMediaFile]:
    return sorted(items, key=lambda item: (
        item.disc or 1,
        item.track if item.track is not None else 9999,
        item.path.name.lower(),
    ))


def _metadata_targets_to_write(
    item: ParsedMediaFile,
    document: NfoDocument,
    album_doc: NfoDocument | None,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> list[Path]:
    targets = [document.target]
    if album_doc is not None:
        targets.append(album_doc.target)
    lyric_target = _lyrics_target(item, candidate)
    if lyric_target is not None:
        targets.append(lyric_target)
    if overwrite:
        return targets
    return [target for target in targets if not target.exists()]


def _write_lyrics(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    overwrite: bool,
) -> bool:
    target = _lyrics_target(item, candidate)
    if target is None:
        return False
    text = candidate.synced_lyrics or candidate.lyrics if candidate else ""
    if not text.strip():
        return False
    if target.exists() and not overwrite:
        return False
    target.write_text(text, encoding="utf-8")
    return True


def _lyrics_target(item: ParsedMediaFile, candidate: ScrapeCandidate | None) -> Path | None:
    if item.media_type != "track" or not candidate:
        return None
    if candidate.synced_lyrics:
        return item.path.with_suffix(".lrc")
    if candidate.lyrics:
        return item.path.with_suffix(".lyrics.txt")
    return None


def _query_from_parsed(item: ParsedMediaFile):
    from mm.organizer.scrapers import ScrapeQuery

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
