from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from mm.db.client import AsyncDBClient
from mm.db.models import JobModel
from mm.organizer.artwork import extract_embedded_artwork
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.organizer.localization import localized_variants
from mm.organizer.metadata_policy import (
    external_track_nfo_candidate,
    local_track_candidate,
    lyrics_query_candidate,
)
from mm.organizer.scrape_writer import (
    _has_cjk,
    _match_key,
    _titles_compatible,
    album_track_metadata_by_path,
    artwork_plans,
    download_ready_artwork,
    metadata_detail,
    write_album_metadata,
    write_external_track_metadata,
    write_standard_metadata,
    write_track_lyrics,
)
from mm.organizer.scrapers import ScrapeCandidate
from mm.server.job_utils import is_cancel_requested, update_job
from mm.server.organizer_assets import _has_artwork
from mm.server.organizer_items import _item_from_parsed
from mm.server.organizer_matching import (
    parsed_from_item,
    query_from_parsed,
    selected_candidate,
)
from mm.server.organizer_music_groups import (
    album_item_from_tracks,
    album_metadata_exists,
    candidate_from_album_nfo,
    music_album_groups,
)
from mm.server.organizer_output_service import artwork_plan_detail
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_schemas import OrganizerItem, OrganizerScrapeJobBody
from mm.server.organizer_scrape_service import OrganizerScrapeService


async def run_scrape_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = OrganizerScrapeJobBody.model_validate_json(row.payload)
        service = OrganizerScrapeService(db, language=body.language)
        if body.items and all(item.media_type in {"album", "track"} for item in body.items):
            await run_music_scrape_job(db, job_id, body, service=service)
            return
        await update_job(db, job_id, status="running", progress=1, message="Starting scrape")
        metadata_count = 0
        artwork_count = 0
        scraper_timeout = service.config.scrapers.timeout
        failures: list[dict[str, str]] = []
        total = max(1, len(body.items) * 2)
        completed = 0
        touched: list[OrganizerItem] = []
        for item in body.items:
            if await is_cancel_requested(db, job_id):
                await update_job(db, job_id, status="canceled", message="Canceled", progress=100)
                return
            parsed = parsed_from_item(item)
            candidate: ScrapeCandidate | None = None
            try:
                selected = selected_candidate(body, item)
                candidate = selected or await service.best_match(parsed, body.source)
                candidate = await service.enrich(
                    candidate,
                    query=query_from_parsed(parsed),
                )
                result = write_standard_metadata(
                    parsed,
                    candidate,
                    overwrite=body.overwrite or selected is not None,
                )
                await update_job(
                    db,
                    job_id,
                    event=False,
                    message="Writing metadata" if result.targets else "Metadata already exists",
                    detail=metadata_detail(result.targets),
                    progress=int(completed / total * 90),
                )
                metadata_count += result.written
            except Exception as exc:  # noqa: BLE001 - preserve per-item failure
                failures.append({"path": item.path, "stage": "metadata", "error": str(exc)})
            completed += 1
            try:
                plans = artwork_plans(parsed, candidate, overwrite=body.overwrite)
                ready_plans = [plan for plan in plans if plan.status == "ready"]
                await update_job(
                    db,
                    job_id,
                    event=False,
                    message="Downloading artwork",
                    detail=artwork_plan_detail(ready_plans),
                    progress=int(completed / total * 90),
                )
                try:
                    artwork_count += await _download_ready_artwork(
                        ready_plans,
                        scraper_timeout,
                    )
                except ArtworkBatchError as exc:
                    artwork_count += exc.completed
                    raise
            except Exception as exc:  # noqa: BLE001 - preserve per-item failure
                failures.append({"path": item.path, "stage": "artwork", "error": str(exc)})
            completed += 1
            if parsed.path.exists():
                refreshed = parse_media_filename(parsed.path)
                if refreshed:
                    touched.append(_item_from_parsed(refreshed))
        if touched:
            await persist_scan_items(db, touched, mark_missing=False, return_items=False)
        status = "completed_with_errors" if failures else "done"
        await update_job(
            db,
            job_id,
            status=status,
            progress=100,
            title="Scrape complete" if not failures else "Scrape completed with failures",
            message=f"Saved {metadata_count} metadata file(s) and {artwork_count} artwork file(s)",
            detail=(failures[0]["path"] if failures else ""),
            result=json.dumps(
                {
                    "metadata": metadata_count,
                    "artwork": artwork_count,
                    "failures": failures,
                },
                ensure_ascii=False,
            ),
            error=f"{len(failures)} item(s) failed" if failures else "",
        )
    except Exception as exc:  # noqa: BLE001 - persist job-level failure
        await update_job(
            db,
            job_id,
            status="error",
            progress=100,
            title="Scrape failed",
            message=str(exc),
            error=str(exc),
        )


async def run_music_scrape_job(
    db: AsyncDBClient,
    job_id: str,
    body: OrganizerScrapeJobBody,
    *,
    service: OrganizerScrapeService | None = None,
) -> None:
    service = service or OrganizerScrapeService(db, language=body.language)
    await update_job(db, job_id, status="running", progress=1, message="Starting album scrape")
    metadata_count = 0
    artwork_count = 0
    scraper_timeout = service.config.scrapers.timeout
    failures: list[dict[str, str]] = []
    groups = music_album_groups(body.items)
    total = max(1, sum(len(items) + 1 for items in groups.values()))
    completed = 0
    touched: list[OrganizerItem] = []
    for items in groups.values():
        if await is_cancel_requested(db, job_id):
            await update_job(db, job_id, status="canceled", message="Canceled", progress=100)
            return
        parsed_items = [parsed_from_item(item) for item in items if item.media_type == "track"]
        if not parsed_items:
            continue
        album_item = album_item_from_tracks(parsed_items)
        try:
            selected = selected_candidate(body, items[0])
            if selected:
                external_candidate = selected
                external_tracks = await service.album_tracks(
                    selected,
                    expected_count=len(parsed_items),
                )
                track_candidates = album_track_metadata_by_path(
                    parsed_items,
                    external_tracks,
                )
            else:
                external_candidate, track_candidates = await _validated_album_candidate(
                    service,
                    album_item,
                    parsed_items,
                    body.source,
                )
            candidate = await service.enrich(
                external_candidate,
                query=query_from_parsed(album_item),
            )
            local_album_candidate = _local_album_candidate(album_item)
            candidate = candidate or local_album_candidate
            individual_candidates = await _individual_track_candidates(
                service,
                [parsed for parsed in parsed_items if parsed.path not in track_candidates],
                body.source,
                candidate,
            )
            if candidate.source == "local" and individual_candidates:
                candidate = _localize_album_artist_from_tracks(
                    candidate,
                    individual_candidates,
                    service.language,
                )
            metadata_overwrite = body.overwrite or selected is not None
            album_complete = (
                not metadata_overwrite
                and album_metadata_exists(album_item)
                and _has_artwork(album_item.path, "album")
            )
            await update_job(
                db,
                job_id,
                message="Searching lyrics" if album_complete else "Writing album metadata",
                detail=album_item.album or album_item.title,
                progress=int(completed / total * 90),
            )
            if album_complete:
                candidate = (
                    candidate_from_album_nfo(album_item) or candidate or local_album_candidate
                )
            else:
                metadata_count += write_album_metadata(
                    album_item,
                    candidate,
                    overwrite=metadata_overwrite,
                )
            track_plan = [
                (
                    parsed,
                    track_candidates.get(parsed.path)
                    or individual_candidates.get(parsed.path)
                    or external_track_nfo_candidate(candidate)
                    or local_track_candidate(candidate, parsed),
                )
                for parsed in parsed_items
            ]
            lyrics_seeds = [
                (parsed, track_nfo_candidate or lyrics_query_candidate(candidate, parsed))
                for parsed, track_nfo_candidate in track_plan
            ]
            lyrics_by_path = await _fetch_album_lyrics(lyrics_seeds, service)
            for parsed, track_nfo_candidate in track_plan:
                will_write_track_nfo = bool(
                    track_nfo_candidate
                    and (
                        metadata_overwrite
                        or not album_complete
                        or not parsed.path.with_suffix(".nfo").exists()
                    )
                )
                await update_job(
                    db,
                    job_id,
                    event=False,
                    message="Writing track NFO" if will_write_track_nfo else "Searching lyrics",
                    detail=parsed.path.name,
                    progress=int(completed / total * 90),
                )
                if will_write_track_nfo:
                    metadata_count += write_external_track_metadata(
                        parsed,
                        track_nfo_candidate,
                        overwrite=metadata_overwrite,
                    )
                metadata_count += write_track_lyrics(
                    parsed,
                    lyrics_by_path.get(parsed.path),
                    overwrite=body.overwrite,
                )
                completed += 1
            if not album_complete:
                embedded_artwork = None
                if not _has_artwork(album_item.path, "album"):
                    embedded_artwork = await asyncio.to_thread(
                        extract_embedded_artwork,
                        [parsed.path for parsed in parsed_items],
                        album_item.path.parent,
                    )
                    if embedded_artwork is not None:
                        artwork_count += 1
                plans = artwork_plans(album_item, candidate, overwrite=body.overwrite)
                ready_plans = [plan for plan in plans if plan.status == "ready"]
                if embedded_artwork is not None and not body.overwrite:
                    ready_plans = []
                await update_job(
                    db,
                    job_id,
                    event=False,
                    message="Downloading album artwork",
                    detail=artwork_plan_detail(ready_plans),
                    progress=int(completed / total * 90),
                )
                try:
                    artwork_count += await _download_ready_artwork(
                        ready_plans,
                        scraper_timeout,
                    )
                except ArtworkBatchError as exc:
                    artwork_count += exc.completed
                    raise
        except Exception as exc:  # noqa: BLE001 - preserve per-album failure
            failures.append({"path": str(album_item.path), "stage": "music", "error": str(exc)})
        completed += 1
        for parsed in parsed_items:
            if parsed.path.exists():
                refreshed = parse_media_filename(parsed.path)
                touched.append(_item_from_parsed(refreshed or parsed))
    if touched:
        await persist_scan_items(db, touched, mark_missing=False, return_items=False)
    status = "completed_with_errors" if failures else "done"
    await update_job(
        db,
        job_id,
        status=status,
        progress=100,
        title="Scrape complete" if not failures else "Scrape completed with failures",
        message=f"Saved {metadata_count} metadata file(s) and {artwork_count} artwork file(s)",
        detail=(failures[0]["path"] if failures else ""),
        result=json.dumps(
            {
                "metadata": metadata_count,
                "artwork": artwork_count,
                "failures": failures,
            },
            ensure_ascii=False,
        ),
        error=f"{len(failures)} album(s) failed" if failures else "",
    )


async def _validated_album_candidate(
    service: OrganizerScrapeService,
    album_item: ParsedMediaFile,
    tracks: list[ParsedMediaFile],
    source: str | None,
) -> tuple[ScrapeCandidate | None, dict[Path, ScrapeCandidate]]:
    candidates = await service.search(
        query_from_parsed(album_item),
        source=source,
        limit=10,
    )
    for candidate in candidates:
        tracklist = await service.album_tracks(
            candidate,
            expected_count=len(tracks),
        )
        matched = album_track_metadata_by_path(tracks, tracklist)
        match_ratio = len(matched) / len(tracks) if tracks else 0
        title_compatible = _titles_compatible(
            album_item.album or album_item.title,
            candidate.album or candidate.title,
        )
        if match_ratio >= 0.5 and title_compatible:
            return (
                _with_local_artist_variants(candidate, album_item),
                matched,
            )
    ordered_tracks = sorted(
        tracks,
        key=lambda track: (
            track.disc or 1,
            track.track if track.track is not None else 9999,
            track.path.name.casefold(),
        ),
    )
    if ordered_tracks and all(track.duration and track.duration > 0 for track in ordered_tracks):
        signature_match = await service.album_by_signature(
            query_from_parsed(album_item),
            [float(track.duration) for track in ordered_tracks if track.duration],
            source=source,
        )
        if signature_match is not None:
            candidate, tracklist = signature_match
            if len(tracklist) == len(ordered_tracks):
                return (
                    _with_local_artist_variants(candidate, album_item),
                    {
                        track.path: _with_local_track_variants(
                            external,
                            track,
                            album_item,
                        )
                        for track, external in zip(
                            ordered_tracks,
                            tracklist,
                            strict=True,
                        )
                    },
                )
    return None, {}


def _with_local_artist_variants(
    candidate: ScrapeCandidate,
    album_item: ParsedMediaFile,
) -> ScrapeCandidate:
    local_artist = album_item.album_artist or album_item.artist or ""
    local_album = album_item.album or album_item.title
    title_variants = dict(candidate.title_variants)
    album_variants = dict(candidate.album_variants or candidate.title_variants)
    artist_variants = dict(candidate.artist_variants)
    album_artist_variants = dict(candidate.album_artist_variants or candidate.artist_variants)
    if local_album:
        title_variants.setdefault("und", local_album)
        album_variants.setdefault("und", local_album)
    if local_artist:
        artist_variants.setdefault("und", local_artist)
        album_artist_variants.setdefault("und", local_artist)
    return replace(
        candidate,
        title_variants=title_variants,
        album_variants=album_variants,
        artist_variants=artist_variants,
        album_artist_variants=album_artist_variants,
    )


def _with_local_track_variants(
    candidate: ScrapeCandidate,
    track: ParsedMediaFile,
    album_item: ParsedMediaFile,
) -> ScrapeCandidate:
    title_variants = dict(candidate.title_variants)
    artist_variants = dict(candidate.artist_variants)
    album_artist_variants = dict(candidate.album_artist_variants or candidate.artist_variants)
    album_variants = dict(candidate.album_variants)
    title_variants.setdefault("und", track.title)
    local_artist = track.artist or album_item.artist or ""
    local_album_artist = track.album_artist or album_item.album_artist or local_artist
    local_album = track.album or album_item.album or album_item.title
    if local_artist:
        artist_variants.setdefault("und", local_artist)
    if local_album_artist:
        album_artist_variants.setdefault("und", local_album_artist)
    if local_album:
        album_variants.setdefault("und", local_album)
    return replace(
        candidate,
        title_variants=title_variants,
        artist_variants=artist_variants,
        album_artist_variants=album_artist_variants,
        album_variants=album_variants,
    )


def _local_album_candidate(item: ParsedMediaFile) -> ScrapeCandidate:
    title = item.album or item.title
    artist = item.album_artist or item.artist or ""
    return ScrapeCandidate(
        source="local",
        source_id="",
        media_type="album",
        title=title,
        artist=artist,
        album_artist=artist,
        album=title,
        year=item.year,
        title_variants=localized_variants(title),
        artist_variants=localized_variants(artist),
        album_artist_variants=localized_variants(artist),
        album_variants=localized_variants(title),
        confidence=1,
    )


def _localize_album_artist_from_tracks(
    album: ScrapeCandidate,
    tracks: dict[Path, ScrapeCandidate],
    language: str,
) -> ScrapeCandidate:
    artists = [candidate.artist for candidate in tracks.values() if candidate.artist]
    if not artists:
        return album
    artist, count = Counter(artists).most_common(1)[0]
    if count / len(artists) < 0.8:
        return album
    variants = dict(album.album_artist_variants or album.artist_variants)
    for candidate in tracks.values():
        if candidate.artist == artist:
            variants.update(candidate.artist_variants)
    variants[language] = artist
    return replace(
        album,
        artist=artist,
        album_artist=artist,
        artist_variants=variants,
        album_artist_variants=variants,
    )


async def _individual_track_candidates(
    service: OrganizerScrapeService,
    tracks: list[ParsedMediaFile],
    source: str | None,
    album_candidate: ScrapeCandidate,
) -> dict[Path, ScrapeCandidate]:
    semaphore = asyncio.Semaphore(_LYRICS_CONCURRENCY)

    async def resolve(
        track: ParsedMediaFile,
    ) -> tuple[Path, ScrapeCandidate | None]:
        async with semaphore:
            candidates = await service.search(
                query_from_parsed(track),
                source=source,
                limit=5,
            )
        matched = next(
            (
                candidate
                for candidate in candidates
                if candidate.confidence >= 0.45
                and _titles_compatible(track.title, candidate.title)
                and _artists_compatible(track.artist, candidate.artist)
            ),
            None,
        )
        if matched is None:
            return track.path, None
        allowed_ids = {
            key: value
            for key, value in matched.external_ids.items()
            if key.endswith(("track", "recording", "artist", "artist_credit")) or key == "isrc"
        }
        return track.path, replace(
            matched,
            album=album_candidate.album or album_candidate.title,
            album_artist=album_candidate.album_artist or album_candidate.artist,
            album_variants=album_candidate.album_variants or album_candidate.title_variants,
            album_artist_variants=album_candidate.album_artist_variants
            or album_candidate.artist_variants,
            external_ids=allowed_ids,
        )

    results = await asyncio.gather(*(resolve(track) for track in tracks))
    return {path: candidate for path, candidate in results if candidate is not None}


def _artists_compatible(local_artist: str | None, candidate_artist: str | None) -> bool:
    local_key = _match_key(local_artist or "")
    candidate_key = _match_key(candidate_artist or "")
    if not local_key or not candidate_key:
        return True
    if _has_cjk(local_key) != _has_cjk(candidate_key):
        return False
    if local_key == candidate_key:
        return True
    from difflib import SequenceMatcher

    return SequenceMatcher(None, local_key, candidate_key).ratio() >= 0.6


_LYRICS_CONCURRENCY = 4
_ARTWORK_CONCURRENCY = 4


@dataclass(frozen=True)
class ArtworkBatchError(RuntimeError):
    completed: int
    errors: tuple[Exception, ...]

    def __str__(self) -> str:
        return str(self.errors[0]) if self.errors else "Artwork download failed"


async def _download_ready_artwork(plans: list, timeout: float) -> int:
    """Download an item's ready artwork plans concurrently (bounded) rather than
    one blocking request at a time."""
    ready = [plan for plan in plans if plan.status == "ready"]
    if not ready:
        return 0
    semaphore = asyncio.Semaphore(_ARTWORK_CONCURRENCY)

    async def download(plan) -> Exception | None:
        async with semaphore:
            try:
                await asyncio.to_thread(download_ready_artwork, [plan], timeout=timeout)
            except Exception as exc:  # noqa: BLE001 - collect all sibling outcomes
                return exc
            return None

    results = await asyncio.gather(*(download(plan) for plan in ready))
    errors = tuple(result for result in results if result is not None)
    completed = len(results) - len(errors)
    if errors:
        raise ArtworkBatchError(completed=completed, errors=errors)
    return completed


async def _fetch_album_lyrics(
    seeds: list[tuple[ParsedMediaFile, ScrapeCandidate | None]],
    service: OrganizerScrapeService,
) -> dict[Path, ScrapeCandidate | None]:
    """Fetch per-track lyrics for an album with bounded concurrency instead of
    one blocking network round-trip per track in sequence."""
    semaphore = asyncio.Semaphore(_LYRICS_CONCURRENCY)

    async def resolve(
        parsed: ParsedMediaFile, seed: ScrapeCandidate | None
    ) -> tuple[Path, ScrapeCandidate | None]:
        if seed is None:
            return parsed.path, None
        async with semaphore:
            enriched = await service.enrich(
                seed,
                query=query_from_parsed(parsed),
            )
        return parsed.path, enriched

    results = await asyncio.gather(*(resolve(parsed, seed) for parsed, seed in seeds))
    return dict(results)
