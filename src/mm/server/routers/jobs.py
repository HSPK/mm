from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header

from mm.db.client import AsyncDBClient
from mm.db.dto import User
from mm.server.dependencies import get_current_user, get_db, require_admin
from mm.server.job_system import job_service
from mm.server.organizer_paths import AuthorizedMediaPath
from mm.server.organizer_schemas import (
    JobEventResponse,
    OrganizerJobResponse,
    OrganizerPlanBody,
    OrganizerScanBody,
    OrganizerScrapeJobBody,
)
from mm.server.utility_schemas import ThumbnailBuildBody

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_admin)],
)


@router.post("/scrape", response_model=OrganizerJobResponse)
async def create_scrape_job(
    body: OrganizerScrapeJobBody,
    background_tasks: BackgroundTasks,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrganizerJobResponse:
    for item in body.items:
        AuthorizedMediaPath.resolve(item.path, must_exist=True, file=True)
    return await job_service.create(
        db,
        kind="scrape",
        title="Scrape",
        payload=body.model_dump_json(),
        background_tasks=background_tasks,
        idempotency_key=idempotency_key,
    )


@router.post("/sync", response_model=OrganizerJobResponse)
async def create_sync_job(
    body: OrganizerScanBody,
    background_tasks: BackgroundTasks,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrganizerJobResponse:
    authorized = [AuthorizedMediaPath.resolve(path, must_exist=True) for path in body.paths]
    if any(path.path != path.root for path in authorized):
        from fastapi import HTTPException

        raise HTTPException(
            400, "Sync requires configured media roots; use /organizer/scan for discovery"
        )
    return await job_service.create(
        db,
        kind="sync",
        title="Sync",
        payload=body.model_dump_json(),
        background_tasks=background_tasks,
        idempotency_key=idempotency_key,
    )


@router.post("/rename", response_model=OrganizerJobResponse)
async def create_rename_job(
    body: OrganizerPlanBody,
    background_tasks: BackgroundTasks,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrganizerJobResponse:
    for item in body.items:
        AuthorizedMediaPath.resolve(item.path, must_exist=True, file=True)
    return await job_service.create(
        db,
        kind="rename",
        title="Rename",
        payload=body.model_dump_json(),
        background_tasks=background_tasks,
        idempotency_key=idempotency_key,
    )


@router.post("/thumbnails", response_model=OrganizerJobResponse)
async def create_thumbnail_job(
    body: ThumbnailBuildBody,
    background_tasks: BackgroundTasks,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerJobResponse:
    return await job_service.create(
        db,
        kind="thumbnails",
        title="Thumbnails",
        payload=body.model_dump_json(),
        background_tasks=background_tasks,
    )


@router.get("", response_model=list[OrganizerJobResponse])
async def jobs(
    limit: int = 20,
    status: str | None = None,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> list[OrganizerJobResponse]:
    return await job_service.list(db, limit=limit, status=status)


@router.get("/{job_id}", response_model=OrganizerJobResponse)
async def job(
    job_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerJobResponse:
    return await job_service.get(db, job_id)


@router.get("/{job_id}/events", response_model=list[JobEventResponse])
async def job_events(
    job_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> list[JobEventResponse]:
    return await job_service.events(db, job_id)


@router.post("/{job_id}/cancel", response_model=OrganizerJobResponse)
async def cancel_job(
    job_id: str,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerJobResponse:
    return await job_service.cancel(db, job_id)


@router.post("/{job_id}/retry", response_model=OrganizerJobResponse)
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    _u: User | None = Depends(get_current_user),
    db: AsyncDBClient = Depends(get_db),
) -> OrganizerJobResponse:
    return await job_service.retry(db, job_id, background_tasks=background_tasks)


async def resume_jobs(db: AsyncDBClient) -> None:
    await job_service.resume_active(db)
