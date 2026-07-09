from __future__ import annotations

from mm.config import load_cli_config
from mm.organizer.artwork import ArtworkPlan, download_artwork, plan_artworks
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.nfo import NfoDocument, build_album_nfo, build_nfo, build_tvshow_nfo, write_nfo
from mm.organizer.scrape_writer import write_track_lyrics
from mm.organizer.scrapers import ScrapeQuery, enrich_candidate
from mm.server.organizer_matching import (
    best_match,
    parsed_from_item,
    query_from_parsed,
    selected_candidate,
)
from mm.server.organizer_schemas import (
    OrganizerApplyResponse,
    OrganizerArtworkOperation,
    OrganizerArtworkPlanResponse,
    OrganizerNfoOperation,
    OrganizerNfoPlanResponse,
    OrganizerPlanBody,
)


def nfo_plan_response(body: OrganizerPlanBody) -> OrganizerNfoPlanResponse:
    parsed_items = [parsed_from_item(item) for item in body.items]
    documents = [
        _build_nfo(
            parsed,
            body.source,
            selected_candidate(body, item),
        )
        for item, parsed in zip(body.items, parsed_items, strict=True)
    ]
    documents.extend(_album_documents(body, parsed_items))
    return OrganizerNfoPlanResponse(
        operations=[_nfo_operation(doc, body.overwrite) for doc in documents]
    )


def apply_nfo(body: OrganizerPlanBody) -> OrganizerApplyResponse:
    parsed_items = [parsed_from_item(item) for item in body.items]
    documents = [
        _build_nfo(
            parsed,
            body.source,
            selected_candidate(body, item),
        )
        for item, parsed in zip(body.items, parsed_items, strict=True)
    ]
    documents.extend(_album_documents(body, parsed_items))
    tvshow_documents: dict[str, NfoDocument] = {}
    for item, parsed in zip(body.items, parsed_items, strict=True):
        if parsed.media_type != "tv":
            continue
        candidate = selected_candidate(body, item) or best_match(parsed, body.source)
        show_candidate = enrich_candidate(
            candidate,
            query=ScrapeQuery(media_type="tv", title=parsed.title),
        )
        document = build_tvshow_nfo(parsed, show_candidate)
        tvshow_documents[str(document.target)] = document
    written = 0
    for document in [*documents, *tvshow_documents.values()]:
        try:
            write_nfo(document, overwrite=body.overwrite)
            written += 1
        except FileExistsError:
            continue
    for body_item, parsed in zip(body.items, parsed_items, strict=True):
        if parsed.media_type != "track":
            continue
        candidate = selected_candidate(body, body_item) or best_match(parsed, body.source)
        enriched = enrich_candidate(candidate, query=query_from_parsed(parsed))
        write_track_lyrics(parsed, enriched, overwrite=body.overwrite)
    return OrganizerApplyResponse(affected=written, message=f"Wrote {written} NFO file(s)")


def artwork_plan_response(body: OrganizerPlanBody) -> OrganizerArtworkPlanResponse:
    plans = [
        plan
        for item in body.items
        for plan in _build_artwork(
            parsed_from_item(item),
            body.source,
            body.overwrite,
            selected_candidate(body, item),
        )
    ]
    return OrganizerArtworkPlanResponse(operations=[_artwork_operation(plan) for plan in plans])


def apply_artwork(body: OrganizerPlanBody) -> OrganizerApplyResponse:
    plans = [
        plan
        for item in body.items
        for plan in _build_artwork(
            parsed_from_item(item),
            body.source,
            body.overwrite,
            selected_candidate(body, item),
        )
    ]
    downloaded = 0
    for plan in plans:
        if plan.status != "ready":
            continue
        download_artwork(plan, timeout=load_cli_config().scrapers.timeout)
        downloaded += 1
    return OrganizerApplyResponse(
        affected=downloaded,
        message=f"Downloaded {downloaded} artwork file(s)",
    )


def artwork_plan_detail(plans: list[ArtworkPlan]) -> str:
    if not plans:
        return "No artwork to download"
    names = [plan.target.name for plan in plans[:3]]
    suffix = f" +{len(plans) - 3}" if len(plans) > 3 else ""
    return ", ".join(names) + suffix


def _build_nfo(
    item: ParsedMediaFile,
    source: str | None,
    selected,
) -> NfoDocument:
    candidate = selected or (best_match(item, source) if source else None)
    enriched = enrich_candidate(candidate, query=query_from_parsed(item))
    return build_nfo(item, enriched)


def _album_documents(
    body: OrganizerPlanBody,
    parsed_items: list[ParsedMediaFile],
) -> list[NfoDocument]:
    documents: dict[str, NfoDocument] = {}
    for body_item, parsed in zip(body.items, parsed_items, strict=True):
        if parsed.media_type != "track":
            continue
        candidate = selected_candidate(body, body_item) or best_match(parsed, body.source)
        enriched = enrich_candidate(candidate, query=query_from_parsed(parsed))
        document = build_album_nfo(parsed, enriched)
        documents[str(document.target)] = document
    return list(documents.values())


def _build_artwork(
    item: ParsedMediaFile,
    source: str | None,
    overwrite: bool,
    selected,
) -> list[ArtworkPlan]:
    candidate = selected or best_match(item, source)
    enriched = enrich_candidate(candidate, query=query_from_parsed(item))
    return plan_artworks(item, enriched, overwrite=overwrite)


def _nfo_operation(document: NfoDocument, overwrite: bool) -> OrganizerNfoOperation:
    if document.target.exists() and not overwrite:
        return OrganizerNfoOperation(
            target=str(document.target),
            media_type=document.media_type,
            status="exists",
            reason="target exists",
        )
    return OrganizerNfoOperation(
        target=str(document.target),
        media_type=document.media_type,
        status="ready",
    )


def _artwork_operation(plan: ArtworkPlan) -> OrganizerArtworkOperation:
    return OrganizerArtworkOperation(
        source_url=plan.source_url,
        target=str(plan.target),
        media_type=plan.media_type,
        status=plan.status,
        reason=plan.reason,
    )
