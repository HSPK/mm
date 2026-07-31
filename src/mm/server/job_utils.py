from __future__ import annotations

import datetime as dt
import json

from mm.db.client import AsyncDBClient
from mm.db.models import JobEventModel, JobModel
from mm.server.organizer_schemas import JobEventResponse, OrganizerJobResponse


async def update_job(
    db: AsyncDBClient, job_id: str, *, event: bool = True, **fields: object
) -> bool:
    fields = {**fields, "updated_at": dt.datetime.now()}
    next_status = fields.get("status")
    condition = JobModel.id == job_id
    terminal = ("done", "error", "canceled", "completed_with_errors")
    if next_status in terminal:
        fields["active_claim"] = None
    if next_status == "canceled":
        condition &= JobModel.status.in_(("queued", "running", "canceling"))
    elif next_status in terminal:
        # A cancellation request wins over a late worker completion/failure.
        condition &= JobModel.status.in_(("queued", "running"))
    else:
        condition &= JobModel.status.in_(("queued", "running", "canceling"))
    affected = await db.objects.execute(JobModel.update(**fields).where(condition))
    if not affected or not event:
        return bool(affected)
    try:
        row = await db.objects.get(JobModel, id=job_id)
    except JobModel.DoesNotExist:
        return False
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
    return True


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
