from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import first_artwork_path
from mm.organizer.scrapers import search_all
from mm.server.dependencies import get_current_user, get_db
from mm.server.organizer_config import organizer_config_response, update_organizer_config_patch
from mm.server.organizer_items import _item_from_parsed, _light_item_from_parsed
from mm.server.organizer_library import organizer_library_groups
from mm.server.organizer_lyrics import lyrics_candidate, safe_audio_path, search_lyrics_source
from mm.server.organizer_matching import candidate_response, parsed_from_item, query_from_item
from mm.server.organizer_media_info import organizer_media_info
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_music import list_music_albums
from mm.server.organizer_output_service import (
    apply_artwork,
    apply_nfo,
    artwork_plan_response,
    nfo_plan_response,
)
from mm.server.organizer_paths import allowed_media_source_path
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
    OrganizerConfigPatch,
    OrganizerConfigResponse,
    OrganizerDetailsBody,
    OrganizerLibraryResponse,
    OrganizerLyricsApplyBody,
    OrganizerLyricsSearchBody,
    OrganizerLyricsSearchResponse,
    OrganizerMatchBody,
    OrganizerMatchResponse,
    OrganizerMatchResult,
    OrganizerMediaInfo,
    OrganizerMusicAlbumsResponse,
    OrganizerNfoPlanResponse,
    OrganizerPlanBody,
    OrganizerRenameLogEntry,
    OrganizerRenamePlanResponse,
    OrganizerScanBody,
    OrganizerScanResponse,
)
from mm.server.routers.player import player_audio, player_file

router = APIRouter(prefix="/api/organizer", tags=["organizer"])


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
    parsed = parse_paths([Path(path) for path in body.paths], recursive=body.recursive)
    context = OrganizerScanContext.create()
    items = [_light_item_from_parsed(item, context) for item in parsed]
    return OrganizerScanResponse(items=await persist_scan_items(db, items))


@router.post("/details", response_model=OrganizerScanResponse)
async def item_details(
    body: OrganizerDetailsBody,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerScanResponse:
    context = OrganizerScanContext.create()
    items = [
        _item_from_parsed(parsed_from_item(item), context).model_copy(
            update={"playback_id": item.playback_id}
        )
        for item in body.items
    ]
    if items:
        await persist_scan_items(db, items, mark_missing=False)
    return OrganizerScanResponse(items=items)


@router.get("/items", response_model=OrganizerScanResponse)
async def items(
    kind: str | None = None,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerScanResponse:
    query = OrganizerMediaModel.select(
        OrganizerMediaModel.id,
        OrganizerMediaModel.path,
        OrganizerMediaModel.source_kind,
        OrganizerMediaModel.media_type,
        OrganizerMediaModel.title,
        OrganizerMediaModel.artist,
        OrganizerMediaModel.album,
        OrganizerMediaModel.year,
        OrganizerMediaModel.season,
        OrganizerMediaModel.episode,
        OrganizerMediaModel.disc,
        OrganizerMediaModel.track,
        OrganizerMediaModel.parse_template,
        OrganizerMediaModel.parse_relative_path,
        OrganizerMediaModel.confidence,
        OrganizerMediaModel.is_new,
        OrganizerMediaModel.has_metadata,
        OrganizerMediaModel.has_images,
        OrganizerMediaModel.has_subtitles,
        OrganizerMediaModel.has_lyrics,
        OrganizerMediaModel.payload,
    ).where(OrganizerMediaModel.missing == 0)
    if kind:
        query = query.where(OrganizerMediaModel.source_kind == kind)
    rows = await db.objects.fetchall(query.order_by(OrganizerMediaModel.path))
    result = [item_from_light_row(row) for row in rows if row.title]
    legacy_ids = [row.id for row in rows if not row.title]
    if legacy_ids:
        legacy_rows = await db.objects.fetchall(
            OrganizerMediaModel.select(OrganizerMediaModel.payload).where(
                OrganizerMediaModel.id.in_(legacy_ids)
            )
        )
        result.extend(compact_item_from_payload(row.payload) for row in legacy_rows)
    return OrganizerScanResponse(items=result)


@router.get("/music/albums", response_model=OrganizerMusicAlbumsResponse)
async def music_albums(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerMusicAlbumsResponse:
    return OrganizerMusicAlbumsResponse(albums=await list_music_albums(db))


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
        items.append(OrganizerArtworkBatchItem(
            playback_id=playback_id,
            thumb_url=f"/api/organizer/artwork/thumb/item/{playback_id}?size={body.size}",
            image_url=f"/api/organizer/artwork/image/item/{playback_id}",
        ))
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


@router.get("/library", response_model=OrganizerLibraryResponse)
async def library_groups(
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerLibraryResponse:
    return await organizer_library_groups(db)


@router.post("/match", response_model=OrganizerMatchResponse)
async def match(
    body: OrganizerMatchBody,
    _u: User | None = Depends(get_current_user),
) -> OrganizerMatchResponse:
    results: list[OrganizerMatchResult] = []
    cfg = load_cli_config()
    if body.language:
        cfg = deepcopy(cfg)
        cfg.scrapers.language = body.language
    for item in body.items:
        candidates = search_all(
            query_from_item(item),
            cfg=cfg,
            source=body.source,
            limit=body.limit,
        )
        results.append(
            OrganizerMatchResult(
                item=item,
                candidates=[candidate_response(candidate) for candidate in candidates],
            )
        )
    return OrganizerMatchResponse(results=results)


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
            candidate
            for candidate in candidates
            if candidate.lyrics or candidate.synced_lyrics
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
    if target.exists() and not body.overwrite:
        return OrganizerApplyResponse(affected=0, message=f"Lyrics already exist: {target.name}")
    target.write_text(text, encoding="utf-8")
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
) -> OrganizerApplyResponse:
    return apply_nfo(body)


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
) -> OrganizerApplyResponse:
    return apply_artwork(body)


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
