from __future__ import annotations

import json

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.models import JobModel
from mm.organizer.filename import parse_media_filename
from mm.organizer.metadata_policy import external_track_nfo_candidate, lyrics_query_candidate
from mm.organizer.scrape_writer import (
    album_track_metadata_by_path,
    artwork_plans,
    download_ready_artwork,
    metadata_detail,
    write_album_metadata,
    write_external_track_metadata,
    write_standard_metadata,
    write_track_lyrics,
)
from mm.organizer.scrapers import ScrapeCandidate, album_track_candidates, enrich_candidate
from mm.server.job_utils import is_cancel_requested, update_job
from mm.server.organizer_assets import _has_artwork
from mm.server.organizer_items import _item_from_parsed
from mm.server.organizer_matching import (
    best_match,
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


async def run_scrape_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = OrganizerScrapeJobBody.model_validate_json(row.payload)
        if body.items and all(item.media_type in {"album", "track"} for item in body.items):
            await run_music_scrape_job(db, job_id, body)
            return
        await update_job(db, job_id, status="running", progress=1, message="Starting scrape")
        metadata_count = 0
        artwork_count = 0
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
                candidate = selected or best_match(parsed, body.source)
                result = write_standard_metadata(
                    parsed,
                    candidate,
                    overwrite=body.overwrite or selected is not None,
                )
                await update_job(
                    db,
                    job_id,
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
                    message="Downloading artwork",
                    detail=artwork_plan_detail(ready_plans),
                    progress=int(completed / total * 90),
                )
                for plan in ready_plans:
                    await update_job(
                        db,
                        job_id,
                        message="Downloading artwork",
                        detail=plan.target.name,
                        progress=int(completed / total * 90),
                    )
                    download_ready_artwork([plan], timeout=load_cli_config().scrapers.timeout)
                    artwork_count += 1
            except Exception as exc:  # noqa: BLE001 - preserve per-item failure
                failures.append({"path": item.path, "stage": "artwork", "error": str(exc)})
            completed += 1
            if parsed.path.exists():
                refreshed = parse_media_filename(parsed.path)
                if refreshed:
                    touched.append(_item_from_parsed(refreshed))
        if touched:
            await persist_scan_items(db, touched, mark_missing=False)
        status = "error" if failures else "done"
        await update_job(
            db,
            job_id,
            status=status,
            progress=100,
            title="Scrape complete" if not failures else "Scrape completed with failures",
            message=f"Saved {metadata_count} metadata file(s) and {artwork_count} artwork file(s)",
            detail=(failures[0]["path"] if failures else ""),
            result=json.dumps({
                "metadata": metadata_count,
                "artwork": artwork_count,
                "failures": failures,
            }, ensure_ascii=False),
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
) -> None:
    await update_job(db, job_id, status="running", progress=1, message="Starting album scrape")
    metadata_count = 0
    artwork_count = 0
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
            external_candidate = selected or best_match(album_item, body.source)
            candidate = external_candidate
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
                candidate = candidate_from_album_nfo(album_item) or external_candidate
            else:
                metadata_count += write_album_metadata(
                    album_item,
                    candidate,
                    overwrite=metadata_overwrite,
                )
            tracklist_candidate = (
                external_candidate
                if external_candidate and external_candidate.source != "local"
                else candidate if candidate and candidate.source != "local" else None
            )
            track_candidates = album_track_metadata_by_path(
                parsed_items,
                album_track_candidates(
                    tracklist_candidate,
                    expected_count=len(parsed_items),
                    cfg=load_cli_config(),
                ),
            )
            for parsed in parsed_items:
                track_nfo_candidate = (
                    track_candidates.get(parsed.path)
                    or external_track_nfo_candidate(candidate)
                )
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
                lyrics_seed = track_nfo_candidate or lyrics_query_candidate(candidate, parsed)
                lyrics_candidate = enrich_candidate(
                    lyrics_seed,
                    query=query_from_parsed(parsed),
                )
                metadata_count += write_track_lyrics(
                    parsed,
                    lyrics_candidate,
                    overwrite=body.overwrite,
                )
                completed += 1
            if not album_complete:
                plans = artwork_plans(album_item, candidate, overwrite=body.overwrite)
                ready_plans = [plan for plan in plans if plan.status == "ready"]
                await update_job(
                    db,
                    job_id,
                    message="Downloading album artwork",
                    detail=artwork_plan_detail(ready_plans),
                    progress=int(completed / total * 90),
                )
                for plan in ready_plans:
                    download_ready_artwork([plan], timeout=load_cli_config().scrapers.timeout)
                    artwork_count += 1
        except Exception as exc:  # noqa: BLE001 - preserve per-album failure
            failures.append({"path": str(album_item.path), "stage": "music", "error": str(exc)})
        completed += 1
        for parsed in parsed_items:
            if parsed.path.exists():
                refreshed = parse_media_filename(parsed.path)
                touched.append(_item_from_parsed(refreshed or parsed))
    if touched:
        await persist_scan_items(db, touched, mark_missing=False)
    status = "error" if failures else "done"
    await update_job(
        db,
        job_id,
        status=status,
        progress=100,
        title="Scrape complete" if not failures else "Scrape completed with failures",
        message=f"Saved {metadata_count} metadata file(s) and {artwork_count} artwork file(s)",
        detail=(failures[0]["path"] if failures else ""),
        result=json.dumps({
            "metadata": metadata_count,
            "artwork": artwork_count,
            "failures": failures,
        }, ensure_ascii=False),
        error=f"{len(failures)} album(s) failed" if failures else "",
    )
