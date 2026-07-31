from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import threading
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import BackgroundTasks, HTTPException
from peewee import IntegrityError

from mm.db.client import AsyncDBClient
from mm.db.models import JobEventModel, JobModel
from mm.server.job_utils import job_event_response, job_response, update_job
from mm.server.organizer_schemas import JobEventResponse, OrganizerJobResponse

TERMINAL_STATUSES = {"done", "error", "canceled", "completed_with_errors"}
ACTIVE_STATUSES = {"queued", "running", "canceling"}

JobRunner = Callable[[AsyncDBClient, str], Awaitable[None]]


@dataclass(frozen=True)
class JobDefinition:
    runner: JobRunner
    resumable: bool


class JobRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, JobDefinition] = {}

    def register(self, kind: str, runner: JobRunner, *, resumable: bool = True) -> None:
        self._definitions[kind] = JobDefinition(runner=runner, resumable=resumable)

    def get(self, kind: str) -> JobDefinition | None:
        return self._definitions.get(kind)


def default_job_registry() -> JobRegistry:
    registry = JobRegistry()

    async def scrape(db: AsyncDBClient, job_id: str) -> None:
        from mm.server.organizer_scrape_jobs import run_scrape_job

        await run_scrape_job(db, job_id)

    async def sync(db: AsyncDBClient, job_id: str) -> None:
        from mm.server.organizer_sync_jobs import run_sync_job

        await run_sync_job(db, job_id)

    async def rename(db: AsyncDBClient, job_id: str) -> None:
        from mm.server.organizer_rename_jobs import run_rename_job

        await run_rename_job(db, job_id)

    async def thumbnails(db: AsyncDBClient, job_id: str) -> None:
        from mm.server.routers.library import _run_thumbnail_job

        await _run_thumbnail_job(db, job_id)

    registry.register("scrape", scrape, resumable=True)
    registry.register("sync", sync, resumable=True)
    registry.register("rename", rename, resumable=False)
    registry.register("thumbnails", thumbnails, resumable=True)
    return registry


class JobService:
    def __init__(self, registry: JobRegistry | None = None) -> None:
        self.registry = registry or default_job_registry()

    async def create(
        self,
        db: AsyncDBClient,
        *,
        kind: str,
        title: str,
        payload: str,
        idempotency_key: str | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> OrganizerJobResponse:
        if self.registry.get(kind) is None:
            raise HTTPException(400, f"Unknown job kind: {kind}")
        canonical_payload = json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical_payload.encode()).hexdigest()
        active_claim = (
            f"{kind}:idempotency:{idempotency_key}"
            if idempotency_key
            else f"{kind}:payload:{payload_hash}"
        )
        existing_query = JobModel.select().where(JobModel.active_claim == active_claim)
        existing = await db.objects.fetchall(existing_query.limit(1))
        if existing:
            return job_response(existing[0])
        job_id = uuid.uuid4().hex
        now = dt.datetime.now()
        try:
            await db.objects.create(
                JobModel,
                id=job_id,
                kind=kind,
                status="queued",
                progress=0,
                title=title,
                message="Queued",
                payload=canonical_payload,
                idempotency_key=idempotency_key,
                payload_hash=payload_hash,
                active_claim=active_claim,
                created_at=now,
                updated_at=now,
            )
        except IntegrityError:
            existing = await db.objects.fetchall(existing_query.limit(1))
            if existing:
                return job_response(existing[0])
            raise
        self.enqueue(db, job_id, background_tasks)
        return await self.get(db, job_id)

    def enqueue(
        self,
        db: AsyncDBClient,
        job_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        thread = threading.Thread(
            target=self._run_in_thread,
            args=(db.database, job_id),
            daemon=True,
            name=f"mm-job-{job_id[:8]}",
        )
        thread.start()

    def _run_in_thread(self, database_target: str, job_id: str) -> None:
        asyncio.run(self._run_with_client(database_target, job_id))

    async def _run_with_client(self, database_target: str, job_id: str) -> None:
        db = AsyncDBClient(database_target)
        await db.connect()
        await self.run(db, job_id)

    async def list(
        self,
        db: AsyncDBClient,
        *,
        limit: int = 20,
        status: str | None = None,
    ) -> list[OrganizerJobResponse]:
        query = JobModel.select()
        if status:
            query = query.where(JobModel.status == status)
        rows = await db.objects.fetchall(
            query.order_by(JobModel.updated_at.desc()).limit(max(1, min(limit, 100)))
        )
        return [job_response(row) for row in rows]

    async def get(self, db: AsyncDBClient, job_id: str) -> OrganizerJobResponse:
        return job_response(await self._get_row(db, job_id))

    async def events(self, db: AsyncDBClient, job_id: str) -> list[JobEventResponse]:
        rows = await db.objects.fetchall(
            JobEventModel.select()
            .join(JobModel)
            .where(JobModel.id == job_id)
            .order_by(JobEventModel.id)
        )
        return [job_event_response(row) for row in rows]

    async def cancel(self, db: AsyncDBClient, job_id: str) -> OrganizerJobResponse:
        row = await self._get_row(db, job_id)
        if row.status in TERMINAL_STATUSES:
            return job_response(row)
        affected = await db.objects.execute(
            JobModel.update(
                status="canceling", message="Cancel requested", updated_at=dt.datetime.now()
            ).where((JobModel.id == job_id) & (JobModel.status.in_(("queued", "running"))))
        )
        if affected:
            await update_job(db, job_id, event=True, message="Cancel requested")
        return await self.get(db, job_id)

    async def retry(
        self,
        db: AsyncDBClient,
        job_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> OrganizerJobResponse:
        row = await self._get_row(db, job_id)
        return await self.create(
            db,
            kind=row.kind,
            title=row.title,
            payload=row.payload,
            background_tasks=background_tasks,
        )

    async def resume_active(self, db: AsyncDBClient) -> None:
        rows = await db.objects.fetchall(
            JobModel.select().where(JobModel.status.in_(ACTIVE_STATUSES))
        )
        for row in rows:
            definition = self.registry.get(row.kind)
            if row.status == "canceling":
                await update_job(db, row.id, status="canceled", progress=100, message="Canceled")
            elif definition and definition.resumable:
                self.enqueue(db, row.id)
            else:
                await update_job(
                    db,
                    row.id,
                    status="error",
                    progress=100,
                    title=f"{row.title} interrupted",
                    message="Job interrupted before completion. Retry manually.",
                    error="interrupted",
                )

    async def run(self, db: AsyncDBClient, job_id: str) -> None:
        try:
            row = await self._get_row(db, job_id)
        except HTTPException:
            return
        if row.status == "canceling":
            await update_job(db, job_id, status="canceled", progress=100, message="Canceled")
            return
        definition = self.registry.get(row.kind)
        if definition is None:
            await update_job(db, job_id, status="error", error=f"Unknown job kind: {row.kind}")
            return
        try:
            await definition.runner(db, job_id)
        except Exception as exc:  # noqa: BLE001 - persist robust job failure
            await update_job(
                db,
                job_id,
                status="error",
                progress=100,
                title=f"{row.title} failed",
                message=str(exc),
                error=str(exc),
            )
            return
        final = await self._get_row(db, job_id)
        if final.status == "canceling":
            await update_job(db, job_id, status="canceled", progress=100, message="Canceled")
        elif final.status not in TERMINAL_STATUSES:
            await update_job(db, job_id, status="done", progress=100, message="Done")

    async def _get_row(self, db: AsyncDBClient, job_id: str) -> JobModel:
        try:
            return await db.objects.get(JobModel, id=job_id)
        except JobModel.DoesNotExist:
            raise HTTPException(404, "Job not found") from None


job_service = JobService()
