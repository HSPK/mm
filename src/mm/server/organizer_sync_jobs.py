from __future__ import annotations

import json
from pathlib import Path

from mm.db.client import AsyncDBClient
from mm.db.models import JobModel
from mm.server.job_utils import is_cancel_requested, update_job
from mm.server.organizer_items import _light_item_from_parsed
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_scan import parse_paths
from mm.server.organizer_schemas import OrganizerItem, OrganizerScanBody


async def run_sync_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = OrganizerScanBody.model_validate_json(row.payload)
        await update_job(db, job_id, status="running", progress=1, message="Scanning sources")
        parsed = parse_paths([Path(path) for path in body.paths], recursive=body.recursive)
        context = OrganizerScanContext.create()
        items: list[OrganizerItem] = []
        total = max(1, len(parsed))
        for index, parsed_item in enumerate(parsed, start=1):
            if await is_cancel_requested(db, job_id):
                await update_job(db, job_id, status="canceled", message="Canceled", progress=100)
                return
            await update_job(
                db,
                job_id,
                message="Reading media metadata",
                detail=parsed_item.path.name,
                progress=int(index / total * 80),
            )
            items.append(_light_item_from_parsed(parsed_item, context))
        await update_job(
            db,
            job_id,
            message="Saving scan results",
            detail=f"{len(items)} item(s)",
            progress=90,
        )
        persisted = await persist_scan_items(db, items)
        await update_job(
            db,
            job_id,
            status="done",
            progress=100,
            title="Sync complete",
            message=f"Synced {len(persisted)} item(s)",
            detail="",
            result=json.dumps({"items": len(persisted)}, ensure_ascii=False),
        )
    except Exception as exc:  # noqa: BLE001 - persist job-level failure
        await update_job(
            db,
            job_id,
            status="error",
            progress=100,
            title="Sync failed",
            message=str(exc),
            error=str(exc),
        )
