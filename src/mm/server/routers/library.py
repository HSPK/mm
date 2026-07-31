"""Library management — switch between library databases."""

from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from mm.config import get_config
from mm.db.backend import DatabaseTarget
from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.db.models import JobModel
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.library.settings import LibraryConfig
from mm.library.thumbnails import build_thumbnail_cache, thumbnail_cache_stats
from mm.media.thumbnails import ffmpeg_available
from mm.server.dependencies import (
    get_current_user,
    get_db,
    invalidate_media_path_cache,
    invalidate_token_cache,
    require_admin,
)
from mm.server.job_utils import update_job
from mm.server.schemas import (
    LibraryInfo,
    SwitchLibraryBody,
    SwitchLibraryResponse,
)
from mm.server.utility_schemas import (
    ThumbnailBuildBody,
    ThumbnailBuildResponse,
    ThumbnailStatusResponse,
    ThumbnailTypeStatus,
)

router = APIRouter(prefix="/api/library", tags=["library"])


async def _run_thumbnail_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = ThumbnailBuildBody.model_validate_json(row.payload)
        await update_job(
            db,
            job_id,
            status="running",
            progress=10,
            message="Building thumbnail cache",
        )
        result = await run_in_threadpool(_build_thumbnails_sync, db.database, body)
        await update_job(
            db,
            job_id,
            status="done",
            progress=100,
            title="Thumbnails complete",
            message=result.message,
            result=json.dumps(result.model_dump(mode="json")),
        )
    except Exception as exc:  # noqa: BLE001
        await update_job(
            db,
            job_id,
            status="error",
            progress=100,
            title="Thumbnails failed",
            message=str(exc),
            error=str(exc),
        )


@router.get("", response_model=LibraryInfo)
async def get_current_library(
    request: Request,
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> LibraryInfo:
    """Return info about the currently active library."""
    db_path = str(getattr(request.app.state, "db_path", ""))
    if not db_path:
        return LibraryInfo(db_path="", name="default", library_id="")
    target = DatabaseTarget.from_value(db_path)
    config = await db.library_config.get()
    return LibraryInfo(
        db_path=target.display,
        name=target.local_path.parent.name if target.local_path else "postgres",
        library_id=config.library_id,
    )


@router.get("/recent", response_model=list[LibraryInfo])
async def list_recent_libraries(
    user: User | None = Depends(get_current_user),
) -> list[LibraryInfo]:
    """Return the list of recently used library paths."""
    raw = os.environ.get("MM_LIBRARIES", "")
    current = os.environ.get("MM_DB", "mm.db")
    paths: list[str] = [p.strip() for p in raw.split(";") if p.strip()]
    if current and current not in paths:
        paths.insert(0, current)

    result: list[LibraryInfo] = []
    for p in paths:
        target = DatabaseTarget.from_value(p)
        if not target.is_local_file or local_storage.exists(target.local_path):
            result.append(
                LibraryInfo(
                    db_path=target.display,
                    name=target.local_path.parent.name
                    if target.local_path and target.local_path.parent != target.local_path
                    else "postgres",
                )
            )
    return result


@router.post("/switch", response_model=SwitchLibraryResponse)
async def switch_library(
    body: SwitchLibraryBody,
    request: Request,
    user: User | None = Depends(require_admin),
) -> SwitchLibraryResponse:
    """Switch the active library database."""
    target = DatabaseTarget.from_value(body.db_path)

    if target.is_local_file and target.local_path and local_storage.is_dir(target.local_path):
        target = DatabaseTarget.from_value(target.local_path / get_config().import_.db_name)

    if target.is_local_file and target.local_path and not local_storage.exists(target.local_path):
        raise HTTPException(status_code=404, detail=f"Database not found: {target.display}")

    if target.is_local_file and target.local_path and not local_storage.is_file(target.local_path):
        raise HTTPException(status_code=400, detail=f"Not a file: {target.display}")

    resolved = target.display

    new_db = AsyncDBClient(resolved)
    await new_db.connect()
    await new_db.init_db()

    old_db: AsyncDBClient | None = getattr(request.app.state, "db", None)
    request.app.state.db = new_db
    request.app.state.db_path = resolved
    request.app.state.config = await new_db.library_config.get()
    os.environ["MM_DB"] = resolved

    invalidate_token_cache()
    invalidate_media_path_cache()
    await _publish_library_change(request, request.app.state.config.library_id)
    if old_db is not None and old_db is not new_db:
        asyncio.create_task(_close_retired_database(old_db))

    return SwitchLibraryResponse(
        db_path=resolved,
        name=target.local_path.parent.name if target.local_path else "postgres",
        library_id=request.app.state.config.library_id,
        message="Library switched successfully",
    )


@router.get("/events")
async def library_events(
    request: Request,
    user: User | None = Depends(get_current_user),
) -> StreamingResponse:
    subscribers = _library_subscribers(request)
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=8)
    subscribers.add(queue)

    async def events():
        try:
            generation = int(getattr(request.app.state, "library_generation", 0))
            config = getattr(request.app.state, "config", None)
            yield _sse_event(
                {
                    "generation": generation,
                    "library_id": getattr(config, "library_id", ""),
                }
            )
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield _sse_event(event)
        finally:
            subscribers.discard(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


async def _publish_library_change(request: Request, library_id: str) -> None:
    generation = int(getattr(request.app.state, "library_generation", 0)) + 1
    request.app.state.library_generation = generation
    event: dict[str, object] = {"generation": generation, "library_id": library_id}
    subscribers = _library_subscribers(request)
    for queue in tuple(subscribers):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(event)


async def _close_retired_database(db: AsyncDBClient) -> None:
    await asyncio.sleep(5)
    await db.close()


def _sse_event(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _library_subscribers(request: Request) -> set[asyncio.Queue[dict[str, object]]]:
    subscribers = getattr(request.app.state, "library_event_subscribers", None)
    if subscribers is None:
        subscribers = set()
        request.app.state.library_event_subscribers = subscribers
    return subscribers


# ── Library config (key-value settings stored in DB) ──────


@router.get("/config", response_model=dict[str, str])
async def get_library_config(
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Return all library config key-value pairs."""
    return (await db.library_config.get()).model_dump(mode="json")


@router.put("/config", response_model=dict[str, str])
async def update_library_config(
    body: dict[str, str],
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict[str, str]:
    """Update one or more library config keys."""
    current = (await db.library_config.get()).model_dump(mode="json")
    config = LibraryConfig.model_validate({**current, **body})
    await db.library_config.set(config)
    return config.model_dump(mode="json")


@router.get("/thumbnails", response_model=ThumbnailStatusResponse)
async def thumbnail_status(
    db: AsyncDBClient = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> ThumbnailStatusResponse:
    config = await db.library_config.get()
    stats = thumbnail_cache_stats(config.library_id, storage=local_storage)
    media_rows = [
        media for media in await db.media.list() if media.id is not None and not media.deleted_at
    ]
    valid_sizes = get_config().thumbnails.sizes
    cache_dir = stats.cache_dir
    return ThumbnailStatusResponse(
        ffmpeg_available=ffmpeg_available(),
        cache_dir=str(stats.cache_dir),
        file_count=stats.file_count,
        total_size=stats.total_size,
        failed_count=stats.failed_count,
        by_type=[
            _thumbnail_type_status(
                "photo",
                [media for media in media_rows if media.media_type.value == "photo"],
                cache_dir,
                len(valid_sizes),
            ),
            _thumbnail_type_status(
                "video",
                [media for media in media_rows if media.media_type.value == "video"],
                cache_dir,
                len(valid_sizes),
            ),
        ],
    )


@router.post("/thumbnails/build", response_model=ThumbnailBuildResponse)
async def build_thumbnails(
    body: ThumbnailBuildBody,
    request: Request,
    user: User | None = Depends(get_current_user),
) -> ThumbnailBuildResponse:
    return await run_in_threadpool(_build_thumbnails_sync, request.app.state.db_path, body)


def _build_thumbnails_sync(db_path: str, body: ThumbnailBuildBody) -> ThumbnailBuildResponse:
    db = DBClient(db_path)
    try:
        config = db.library_config.get()
        result = build_thumbnail_cache(
            db,
            config.library_root,
            config.library_id,
            sizes=body.sizes,
            force=body.force,
            media_types={"video"} if body.videos_only else None,
            failed_only=body.failed_only,
            storage=local_storage,
        )
        stats = thumbnail_cache_stats(config.library_id, storage=local_storage)
        return ThumbnailBuildResponse(
            total=result.total,
            generated=result.generated,
            cached=result.cached,
            failed=result.failed,
            failed_count=stats.failed_count,
            message=(
                f"{result.generated} generated, {result.cached} cached, {result.failed} failed."
            ),
        )
    finally:
        db.close()


def _thumbnail_type_status(
    media_type: str,
    media_rows: list,
    cache_dir,
    size_count: int,
) -> ThumbnailTypeStatus:
    cached_files = 0
    failed_count = 0
    sizes = get_config().thumbnails.sizes
    for media in media_rows:
        media_id = media.id
        if media_id is None:
            continue
        for size in sizes:
            if local_storage.exists(cache_dir / size / f"{media_id}.webp"):
                cached_files += 1
        if media_type == "video" and local_storage.exists(
            cache_dir / "failed" / "poster" / f"{media_id}.txt"
        ):
            failed_count += 1
    return ThumbnailTypeStatus(
        media_type=media_type,
        media_count=len(media_rows),
        expected_files=len(media_rows) * size_count,
        cached_files=cached_files,
        failed_count=failed_count,
    )
