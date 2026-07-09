from __future__ import annotations

import datetime as dt
import json

from mm.db.client import AsyncDBClient
from mm.db.models import JobEventModel, JobModel
from mm.server.organizer_schemas import JobEventResponse, OrganizerJobResponse


async def update_job(db: AsyncDBClient, job_id: str, **fields: object) -> None:
    fields = {**fields, "updated_at": dt.datetime.now()}
    await db.objects.execute(JobModel.update(**fields).where(JobModel.id == job_id))
    try:
        row = await db.objects.get(JobModel, id=job_id)
    except JobModel.DoesNotExist:
        return
    await db.objects.create(
        JobEventModel,
        job=row,
        status=row.status,
        progress=row.progress,
        message=row.message,
        detail=row.detail,
        error=row.error,
        created_at=dt.datetime.now(),
    )


async def is_cancel_requested(db: AsyncDBClient, job_id: str) -> bool:
    try:
        row = await db.objects.get(JobModel, id=job_id)
    except JobModel.DoesNotExist:
        return True
    return row.status == "canceling"


def job_response(row: JobModel) -> OrganizerJobResponse:
    try:
        result = json.loads(row.result or "{}")
    except json.JSONDecodeError:
        result = {}
    return OrganizerJobResponse(
        id=row.id,
        kind=row.kind,
        status=row.status,
        progress=row.progress,
        title=row.title,
        message=row.message,
        detail=row.detail,
        result=result,
        error=row.error,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def job_event_response(row: JobEventModel) -> JobEventResponse:
    return JobEventResponse(
        id=row.id,
        job_id=row.job.id,
        status=row.status,
        progress=row.progress,
        message=row.message,
        detail=row.detail,
        error=row.error,
        created_at=row.created_at.isoformat(),
    )
