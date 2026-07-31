from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import first_artwork_path
from mm.server.dependencies import get_current_user, get_db, require_admin
from mm.server.file_manager import is_local_request, open_in_file_manager
from mm.server.organizer_capabilities import capabilities_response
from mm.server.organizer_config import organizer_config_response, update_organizer_config_patch
from mm.server.organizer_items import _item_from_parsed, _light_item_from_parsed
from mm.server.organizer_lyrics import (
    lyrics_candidate,
    safe_audio_path,
    search_lyrics_source,
)
from mm.server.organizer_matching import parsed_from_item
from mm.server.organizer_media_info import organizer_media_info
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_output_service import (
    apply_artwork,
    apply_nfo,
    artwork_plan_response,
    nfo_plan_response,
)
from mm.server.organizer_paths import AuthorizedMediaPath, allowed_media_source_path
from mm.server.organizer_persistence import (
    compact_item_from_payload,
    item_from_light_row,
    persist_scan_items,
)
from mm.server.organizer_rename_jobs import (
    apply_rename_body,
    rename_log_entries,
    rename_plan_for_items,
    rename_plan_response,
    undo_rename_batch,
)
from mm.server.organizer_scan import parse_paths, refresh_organizer_item
from mm.server.organizer_schemas import (
    OrganizerApplyResponse,
    OrganizerArtworkBatchBody,
    OrganizerArtworkBatchItem,
    OrganizerArtworkBatchResponse,
    OrganizerArtworkPlanResponse,
    OrganizerCandidate,
    OrganizerConfigPatch,
    OrganizerConfigResponse,
    OrganizerDetailsBody,
    OrganizerItem,
    OrganizerItemPatch,
    OrganizerItemPatchRequest,
    OrganizerItemsPatchBody,
    OrganizerItemsPatchResponse,
    OrganizerItemsResponse,
    OrganizerLyricsApplyBody,
    OrganizerLyricsSearchBody,
    OrganizerLyricsSearchResponse,
    OrganizerMatchBody,
    OrganizerMatchResponse,
    OrganizerMediaInfo,
    OrganizerNfoPlanResponse,
    OrganizerPlanBody,
    OrganizerRenameLogEntry,
    OrganizerRenamePlanResponse,
    OrganizerRevealDirectoryBody,
    OrganizerScanBody,
    OrganizerScanResponse,
)
from mm.server.organizer_scrape_service import OrganizerScrapeService
from mm.server.routers.player import player_audio, player_file

router = APIRouter(
    prefix="/api/organizer",
    tags=["organizer"],
    dependencies=[Depends(require_admin)],
)


@router.get("/capabilities")
async def capabilities(
    _u: User | None = Depends(get_current_user),
) -> dict[str, object]:
    return capabilities_response()


@router.get("/config", response_model=OrganizerConfigResponse)
async def get_organizer_config(
    _u: User | None = Depends(get_current_user),
) -> OrganizerConfigResponse:
    return organizer_config_response()


@router.put("/config", response_model=OrganizerConfigResponse)
async def update_organizer_config(
    body: OrganizerConfigPatch,
    _u: User | None = Depends(get_current_user),
) -> OrganizerConfigResponse:
    return update_organizer_config_patch(body)


@router.post("/scan", response_model=OrganizerScanResponse)
async def scan(
    body: OrganizerScanBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerScanResponse:
    paths = [AuthorizedMediaPath.resolve(path, must_exist=True).path for path in body.paths]
    parsed = parse_paths(paths, recursive=body.recursive)
    context = OrganizerScanContext.create()
    items = [_light_item_from_parsed(item, context) for item in parsed]
    # /scan is intentionally ad-hoc discovery. It never reconciles missing
    # rows; only a full configured-root sync job does that.
    return OrganizerScanResponse(items=await persist_scan_items(db, items, mark_missing=False))


@router.post("/details", response_model=OrganizerScanResponse)
async def item_details(
    body: OrganizerDetailsBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerScanResponse:
    for item in body.items:
        AuthorizedMediaPath.resolve(item.path, must_exist=True, file=True)
    context = OrganizerScanContext.create()
    items = [
        _item_from_parsed(parsed_from_item(item), context).model_copy(
            update={
                "playback_id": item.playback_id,
                "item_uid": item.item_uid,
                "revision": item.revision,
            }
        )
        for item in body.items
    ]
    return OrganizerScanResponse(items=items)


@router.get("/items", response_model=OrganizerItemsResponse)
async def items(
    kind: str | None = None,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerItemsResponse:
    db_query = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.item_uid,
        OrganizerMediaModel.revision,
        OrganizerMediaModel.path,
        OrganizerMediaModel.source_kind,
        OrganizerMediaModel.media_type,
        OrganizerMediaModel.title,
        OrganizerMediaModel.artist,
        OrganizerMediaModel.album_artist,
        OrganizerMediaModel.album,
        OrganizerMediaModel.year,
        OrganizerMediaModel.season,
        OrganizerMediaModel.episode,
        OrganizerMediaModel.disc,
        OrganizerMediaModel.track,
        OrganizerMediaModel.parse_template,
        OrganizerMediaModel.parse_relative_path,
        OrganizerMediaModel.confidence,
        OrganizerMediaModel.audio_duration,
        OrganizerMediaModel.audio_mime_type,
        OrganizerMediaModel.is_new,
        OrganizerMediaModel.has_metadata,
        OrganizerMediaModel.has_images,
        OrganizerMediaModel.has_subtitles,
        OrganizerMediaModel.has_lyrics,
        OrganizerMediaModel.payload,
    ).where(OrganizerMediaModel.missing == 0)
    if kind:
        db_query = db_query.where(OrganizerMediaModel.source_kind == kind)
    rows = await db.objects.fetchall(db_query.order_by(OrganizerMediaModel.path))
    result = [item_from_light_row(row) for row in rows if row.title]
    legacy_ids = [row.id for row in rows if not row.title]
    if legacy_ids:
        legacy_rows = await db.objects.fetchall(
            OrganizerMediaModel.select(OrganizerMediaModel.payload).where(
                OrganizerMediaModel.id.in_(legacy_ids)
            )
        )
        result.extend(compact_item_from_payload(row.payload) for row in legacy_rows)
    return OrganizerItemsResponse(items=result)


@router.post("/reveal-directory")
async def reveal_item_directory(
    body: OrganizerRevealDirectoryBody,
    request: Request,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> dict[str, bool]:
    if not is_local_request(request):
        raise HTTPException(403, "Opening the file manager is only available on the local machine")
    item_uids = list(dict.fromkeys(body.item_uids))
    rows = await db.objects.fetchall(
        OrganizerMediaModel.select(
            OrganizerMediaModel.item_uid,
            OrganizerMediaModel.path,
        ).where(OrganizerMediaModel.item_uid.in_(item_uids))
    )
    if len(rows) != len(item_uids):
        raise HTTPException(404, "Organizer item not found")
    authorized = [AuthorizedMediaPath.resolve(row.path, must_exist=True, file=True) for row in rows]
    if len({item.root for item in authorized}) != 1:
        raise HTTPException(400, "Album files must belong to the same media source")
    try:
        directory = Path(os.path.commonpath([str(item.path.parent) for item in authorized]))
    except ValueError as exc:
        raise HTTPException(400, "Album files do not share a directory") from exc
    if not await asyncio.to_thread(open_in_file_manager, directory):
        raise HTTPException(422, "Could not open the system file manager")
    return {"revealed": True}


@router.patch("/items", response_model=OrganizerItemsPatchResponse)
async def patch_items(
    body: OrganizerItemsPatchBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerItemsPatchResponse:
    if not body.items:
        return OrganizerItemsPatchResponse(items=[])
    uids = [request.item_uid for request in body.items]
    if len(set(uids)) != len(uids):
        raise HTTPException(400, "Duplicate organizer item uid")
    rows = await db.objects.fetchall(
        OrganizerMediaModel.select().where(OrganizerMediaModel.item_uid.in_(uids))
    )
    rows_by_uid = {row.item_uid: row for row in rows}
    if len(rows_by_uid) != len(uids):
        raise HTTPException(404, "Organizer item not found")
    for request in body.items:
        if rows_by_uid[request.item_uid].revision != request.revision:
            raise HTTPException(409, "Organizer item revision conflict")

    updated: list[OrganizerItem] = []
    async with db.objects.transaction():
        for request in body.items:
            updated.append(await _patch_projection(db, rows_by_uid[request.item_uid], request))
    for request, item in zip(body.items, updated, strict=True):
        if request.write_nfo:
            await _write_projection_nfo(db, item)
    if any(request.write_nfo for request in body.items):
        refreshed_rows = await db.objects.fetchall(
            OrganizerMediaModel.select().where(OrganizerMediaModel.item_uid.in_(uids))
        )
        refreshed = {row.item_uid: item_from_light_row(row) for row in refreshed_rows}
        updated = [refreshed[item_uid] for item_uid in uids]
    return OrganizerItemsPatchResponse(items=updated)


@router.patch("/items/{item_uid}", response_model=OrganizerItem)
async def patch_item(
    item_uid: str,
    body: OrganizerItemPatch,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerItem:
    try:
        row = await db.objects.get(OrganizerMediaModel, item_uid=item_uid)
    except OrganizerMediaModel.DoesNotExist as exc:
        raise HTTPException(404, "Organizer item not found") from exc
    updated = await _patch_projection(
        db,
        row,
        OrganizerItemPatchRequest(
            item_uid=item_uid,
            **body.model_dump(exclude_unset=True),
        ),
    )
    if body.write_nfo:
        await _write_projection_nfo(db, updated)
        refreshed = await db.objects.get(OrganizerMediaModel, item_uid=item_uid)
        return item_from_light_row(refreshed)
    return updated


async def _patch_projection(
    db: AsyncDBClient,
    row: OrganizerMediaModel,
    request: OrganizerItemPatchRequest,
) -> OrganizerItem:
    AuthorizedMediaPath.resolve(row.path, must_exist=True, file=True)
    item = compact_item_from_payload(row.payload).model_copy(
        update={
            "path": row.path,
            "item_uid": row.item_uid,
            "revision": row.revision,
            "playback_id": str(row.id) if row.id is not None else None,
        }
    )
    updates = request.model_dump(
        exclude={"item_uid", "revision", "write_nfo"},
        exclude_unset=True,
    )
    item = item.model_copy(update=updates)
    revision = row.revision + 1
    item = item.model_copy(update={"revision": revision})
    payload = item.model_dump(mode="json")
    affected = await db.objects.execute(
        OrganizerMediaModel.update(
            title=item.title,
            artist=item.artist,
            album_artist=item.album_artist,
            album=item.album,
            year=item.year,
            music_title_variants=json.dumps(
                item.metadata_title_variants,
                ensure_ascii=False,
            ),
            music_artist_variants=json.dumps(
                item.metadata_artist_variants,
                ensure_ascii=False,
            ),
            music_album_artist_variants=json.dumps(
                item.metadata_album_artist_variants,
                ensure_ascii=False,
            ),
            music_album_variants=json.dumps(
                item.metadata_album_variants,
                ensure_ascii=False,
            ),
            payload=json.dumps(payload, ensure_ascii=False),
            revision=revision,
        ).where(
            (OrganizerMediaModel.item_uid == request.item_uid)
            & (OrganizerMediaModel.revision == request.revision)
        )
    )
    if affected != 1:
        raise HTTPException(409, "Organizer item revision conflict")
    return item


async def _write_projection_nfo(db: AsyncDBClient, item: OrganizerItem) -> None:
    candidate = OrganizerCandidate(
        source=item.metadata_rating_source or "organizer-projection",
        source_id=item.item_uid or item.path,
        media_type=item.media_type,
        title=item.metadata_title or item.title,
        original_title=item.metadata_original_title or "",
        show_title=item.metadata_show_title or "",
        artist=item.artist or "",
        album_artist=item.album_artist or item.artist or "",
        album=item.album or "",
        year=item.metadata_year or item.year,
        overview=item.metadata_plot or "",
        tagline=item.metadata_tagline or "",
        release_date=item.metadata_premiered or "",
        certification=item.metadata_certification or "",
        runtime=item.metadata_runtime,
        status=item.metadata_status or "",
        genres=item.metadata_genres or [],
        countries=item.metadata_countries or [],
        studios=item.metadata_studios or [],
        tags=item.metadata_tags or [],
        external_ids=item.metadata_ids or {},
        cast=[{"name": name} for name in item.metadata_cast or []],
        rating=item.metadata_rating,
        confidence=1.0,
        title_variants=item.metadata_title_variants,
        artist_variants=item.metadata_artist_variants,
        album_artist_variants=item.metadata_album_artist_variants,
        album_variants=item.metadata_album_variants,
    )
    await apply_nfo(
        db,
        OrganizerPlanBody(
            items=[item],
            overwrite=True,
            selected_candidates={item.path: candidate},
        ),
    )


@router.get("/artwork/image")
async def artwork_image(
    path: str,
    _u: User | None = Depends(get_current_user),
) -> FileResponse:
    image_path = Path(path).expanduser().resolve()
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(400, "Unsupported artwork file")
    if not image_path.is_file():
        raise HTTPException(404, "Artwork not found")
    if not allowed_media_source_path(image_path):
        raise HTTPException(403, "Artwork is outside configured media sources")
    return FileResponse(str(image_path))


@router.get("/artwork/image/item/{playback_id}")
async def artwork_image_for_item(
    playback_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    image_path = await _artwork_path_for_playback_id(db, playback_id)
    return FileResponse(str(image_path))


@router.get("/artwork/thumb")
async def artwork_thumb(
    path: str,
    size: int = 320,
    _u: User | None = Depends(get_current_user),
) -> FileResponse:
    image_path = Path(path).expanduser().resolve()
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(400, "Unsupported artwork file")
    if not image_path.is_file():
        raise HTTPException(404, "Artwork not found")
    if not allowed_media_source_path(image_path):
        raise HTTPException(403, "Artwork is outside configured media sources")
    from mm.organizer.artwork_cache import artwork_thumbnail

    thumb_path = await asyncio.to_thread(artwork_thumbnail, image_path, size)
    if thumb_path is None:
        raise HTTPException(422, "Artwork thumbnail could not be generated")
    return FileResponse(
        str(thumb_path),
        media_type="image/webp",
        headers={"Cache-Control": load_cli_config().thumbnails.http_cache_control},
    )


@router.get("/artwork/thumb/item/{playback_id}")
async def artwork_thumb_for_item(
    playback_id: str,
    size: int = 320,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> FileResponse:
    from mm.organizer.artwork_cache import artwork_thumbnail

    image_path = await _artwork_path_for_playback_id(db, playback_id)
    thumb_path = await asyncio.to_thread(artwork_thumbnail, image_path, size)
    if thumb_path is None:
        raise HTTPException(422, "Artwork thumbnail could not be generated")
    return FileResponse(
        str(thumb_path),
        media_type="image/webp",
        headers={"Cache-Control": load_cli_config().thumbnails.http_cache_control},
    )


@router.post("/artwork/batch", response_model=OrganizerArtworkBatchResponse)
async def artwork_batch(
    body: OrganizerArtworkBatchBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerArtworkBatchResponse:
    items: list[OrganizerArtworkBatchItem] = []
    for playback_id in dict.fromkeys(body.playback_ids):
        try:
            await _artwork_path_for_playback_id(db, playback_id)
        except HTTPException:
            items.append(OrganizerArtworkBatchItem(playback_id=playback_id))
            continue
        items.append(
            OrganizerArtworkBatchItem(
                playback_id=playback_id,
                thumb_url=f"/api/organizer/artwork/thumb/item/{playback_id}?size={body.size}",
                image_url=f"/api/organizer/artwork/image/item/{playback_id}",
            )
        )
    return OrganizerArtworkBatchResponse(items=items)


@router.get("/media-info", response_model=OrganizerMediaInfo | None)
async def media_info(
    playback_id: str = "",
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerMediaInfo | None:
    media_path = await _media_path_for_playback_id(db, playback_id)
    if not media_path.is_file():
        raise HTTPException(404, "Media file not found")
    if not allowed_media_source_path(media_path):
        raise HTTPException(403, "Media file is outside configured media sources")
    return organizer_media_info(media_path)


@router.get("/file")
async def organizer_file(
    request: Request,
    path: str,
    _u: User | None = Depends(get_current_user),
):
    return await player_file(request, path, _u)


@router.get("/audio")
async def organizer_audio(
    request: Request,
    path: str,
    _u: User | None = Depends(get_current_user),
):
    return await player_audio(request, path, _u)


@router.post("/match", response_model=OrganizerMatchResponse)
async def match(
    body: OrganizerMatchBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerMatchResponse:
    service = OrganizerScrapeService(db, language=body.language)
    return OrganizerMatchResponse(
        results=await service.match_items(
            body.items,
            source=body.source,
            limit=body.limit,
        )
    )


@router.post("/lyrics/search", response_model=OrganizerLyricsSearchResponse)
async def lyrics_search(
    body: OrganizerLyricsSearchBody,
    _u: User | None = Depends(get_current_user),
) -> OrganizerLyricsSearchResponse:
    safe_audio_path(body.path)
    raw_candidates = search_lyrics_source(
        body.source,
        body.title,
        body.artist,
        body.album,
        limit=max(1, min(body.limit, 10)),
    )
    if not raw_candidates and body.album:
        raw_candidates = search_lyrics_source(
            body.source,
            body.title,
            body.artist,
            "",
            limit=max(1, min(body.limit, 10)),
        )
    candidates = []
    seen: set[str] = set()
    for item in raw_candidates:
        candidate = lyrics_candidate(item, body.title, body.artist, body.album)
        key = candidate.source_id
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return OrganizerLyricsSearchResponse(
        candidates=[
            candidate for candidate in candidates if candidate.lyrics or candidate.synced_lyrics
        ]
    )


@router.post("/lyrics/apply", response_model=OrganizerApplyResponse)
async def lyrics_apply(
    body: OrganizerLyricsApplyBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerApplyResponse:
    media_path = safe_audio_path(body.path)
    text = body.synced_lyrics or body.lyrics
    if not text.strip():
        raise HTTPException(400, "No lyrics provided")
    target = media_path.with_suffix(".lrc" if body.synced_lyrics else ".lyrics.txt")
    AuthorizedMediaPath.resolve(media_path, must_exist=True, file=True).output(target)
    if target.exists() and not body.overwrite:
        return OrganizerApplyResponse(affected=0, message=f"Lyrics already exist: {target.name}")
    await asyncio.to_thread(target.write_text, text, encoding="utf-8")
    await refresh_organizer_item(db, media_path)
    return OrganizerApplyResponse(affected=1, message=f"Saved lyrics: {target.name}")


@router.post("/rename/plan", response_model=OrganizerRenamePlanResponse)
async def rename_plan(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
) -> OrganizerRenamePlanResponse:
    return rename_plan_response(
        rename_plan_for_items([parsed_from_item(item) for item in body.items], body.root)
    )


@router.post("/rename/apply", response_model=OrganizerApplyResponse)
async def rename_apply(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerApplyResponse:
    return await apply_rename_body(db, body)


@router.get("/rename/logs", response_model=list[OrganizerRenameLogEntry])
async def rename_logs(
    limit: int = 10,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> list[OrganizerRenameLogEntry]:
    return await rename_log_entries(db, limit=limit)


@router.post("/rename/undo/{batch_id}", response_model=OrganizerApplyResponse)
async def rename_undo(
    batch_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerApplyResponse:
    return await undo_rename_batch(db, batch_id)


@router.post("/nfo/plan", response_model=OrganizerNfoPlanResponse)
async def nfo_plan(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
) -> OrganizerNfoPlanResponse:
    return nfo_plan_response(body)


@router.post("/nfo/apply", response_model=OrganizerApplyResponse)
async def nfo_apply(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerApplyResponse:
    return await apply_nfo(db, body)


@router.post("/artwork/plan", response_model=OrganizerArtworkPlanResponse)
async def artwork_plan(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
) -> OrganizerArtworkPlanResponse:
    return artwork_plan_response(body)


@router.post("/artwork/apply", response_model=OrganizerApplyResponse)
async def artwork_apply(
    body: OrganizerPlanBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerApplyResponse:
    return await apply_artwork(db, body)


async def _artwork_path_for_playback_id(db: AsyncDBClient, playback_id: str) -> Path:
    row = await _organizer_media_row(db, playback_id)
    artwork_path = first_artwork_path(Path(row.path), row.media_type)
    if artwork_path is None:
        raise HTTPException(404, "Artwork not found")
    if not allowed_media_source_path(artwork_path):
        raise HTTPException(403, "Artwork is outside configured media sources")
    return artwork_path


async def _media_path_for_playback_id(db: AsyncDBClient, playback_id: str) -> Path:
    row = await _organizer_media_row(db, playback_id)
    return Path(row.path).expanduser().resolve()


async def _organizer_media_row(db: AsyncDBClient, playback_id: str) -> OrganizerMediaModel:
    try:
        organizer_id = int(playback_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid playback id") from exc
    try:
        return await db.objects.get(OrganizerMediaModel, id=organizer_id)
    except OrganizerMediaModel.DoesNotExist as exc:
        raise HTTPException(404, "Playback item not found") from exc
