from __future__ import annotations

import datetime as dt
import json
import shutil
import uuid
from dataclasses import replace
from pathlib import Path

from fastapi import HTTPException

from mm.config import load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.models import JobModel, OrganizerMediaModel, OrganizerRenameLogModel
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.organizer.rename import (
    RenameOperation,
    RenamePlan,
    apply_rename_operations,
    plan_renames,
    plan_renames_with_source_roots,
    remove_empty_source_dirs,
)
from mm.server.job_utils import is_cancel_requested, update_job
from mm.server.organizer_items import _light_item_from_parsed
from mm.server.organizer_matching import parsed_from_item
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_schemas import (
    OrganizerApplyResponse,
    OrganizerPlanBody,
    OrganizerRenameLogEntry,
    OrganizerRenameOperation,
    OrganizerRenamePlanResponse,
)
from mm.server.organizer_sources import configured_roots_for_items, source_kind_for_item


def rename_plan_for_items(items: list[ParsedMediaFile], root: str | None) -> RenamePlan:
    cfg = load_cli_config()
    if root:
        return plan_renames(
            items,
            root=Path(root),
            templates=cfg.organizer.templates,
        )
    return plan_renames_with_source_roots(
        items,
        roots=configured_roots_for_items(items, cfg),
        templates=cfg.organizer.templates,
    )


def rename_plan_response(plan: RenamePlan) -> OrganizerRenamePlanResponse:
    return OrganizerRenamePlanResponse(
        root=str(plan.root),
        operations=[
            OrganizerRenameOperation(
                source=str(op.source),
                target=str(op.target),
                media_type=op.media_type,
                status=op.status,
                reason=op.reason,
            )
            for op in plan.operations
        ],
        ready=len(plan.actionable),
        conflicts=len(plan.conflicts),
    )


async def apply_rename_body(
    db: AsyncDBClient,
    body: OrganizerPlanBody,
) -> OrganizerApplyResponse:
    parsed = [parsed_from_item(item) for item in body.items]
    plan = rename_plan_for_items(parsed, body.root)
    if plan.conflicts:
        raise HTTPException(409, "Rename plan has conflicts")
    applied = apply_rename_operations(plan)
    await refresh_after_rename(db, parsed, applied)
    batch_id = uuid.uuid4().hex
    for operation in applied:
        await db.objects.create(
            OrganizerRenameLogModel,
            batch_id=batch_id,
            source=str(operation.source),
            target=str(operation.target),
            media_type=operation.media_type,
            status="applied",
        )
    return OrganizerApplyResponse(
        affected=len(applied),
        message=f"Renamed {len(applied)} file(s). Batch {batch_id}",
        batch_id=batch_id,
    )


async def rename_log_entries(
    db: AsyncDBClient,
    *,
    limit: int = 10,
) -> list[OrganizerRenameLogEntry]:
    rows = await db.objects.fetchall(
        OrganizerRenameLogModel.select()
        .order_by(OrganizerRenameLogModel.created_at.desc(), OrganizerRenameLogModel.id.desc())
        .limit(max(1, min(limit * 20, 500)))
    )
    grouped: dict[str, list[OrganizerRenameLogModel]] = {}
    for row in rows:
        grouped.setdefault(row.batch_id, []).append(row)
    entries: list[OrganizerRenameLogEntry] = []
    for batch_id, batch_rows in grouped.items():
        latest = max(row.created_at for row in batch_rows)
        status = "undone" if all(row.status == "undone" for row in batch_rows) else "applied"
        entries.append(
            OrganizerRenameLogEntry(
                batch_id=batch_id,
                created_at=latest.isoformat(),
                count=len(batch_rows),
                status=status,
            )
        )
    return sorted(entries, key=lambda entry: entry.created_at, reverse=True)[:limit]


async def undo_rename_batch(
    db: AsyncDBClient,
    batch_id: str,
) -> OrganizerApplyResponse:
    rows = await db.objects.fetchall(
        OrganizerRenameLogModel.select()
        .where(
            (OrganizerRenameLogModel.batch_id == batch_id)
            & (OrganizerRenameLogModel.status == "applied")
        )
        .order_by(OrganizerRenameLogModel.id.desc())
    )
    undone = 0
    now = dt.datetime.now()
    for row in rows:
        target = Path(row.target)
        source = Path(row.source)
        if not target.exists() or source.exists():
            continue
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(source))
        await db.objects.execute(
            OrganizerRenameLogModel.update(status="undone", undone_at=now).where(
                OrganizerRenameLogModel.id == row.id
            )
        )
        undone += 1
    return OrganizerApplyResponse(affected=undone, message=f"Restored {undone} file(s)")


async def run_rename_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = OrganizerPlanBody.model_validate_json(row.payload)
        await update_job(db, job_id, status="running", progress=10, message="Planning rename")
        parsed = [parsed_from_item(item) for item in body.items]
        plan = rename_plan_for_items(parsed, body.root)
        if plan.conflicts:
            await update_job(
                db,
                job_id,
                status="error",
                progress=100,
                title="Rename failed",
                message=f"Rename has {len(plan.conflicts)} conflict(s)",
                error="rename conflicts",
            )
            return
        applied: list[RenameOperation] = []
        total = max(1, len(plan.actionable))
        batch_id = uuid.uuid4().hex
        for index, operation in enumerate(plan.actionable, start=1):
            if await is_cancel_requested(db, job_id):
                await update_job(db, job_id, status="canceled", message="Canceled", progress=100)
                return
            await update_job(
                db,
                job_id,
                message="Renaming files",
                detail=operation.source.name,
                progress=10 + int(index / total * 80),
            )
            operation.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(operation.source), str(operation.target))
            applied.append(operation)
            await db.objects.create(
                OrganizerRenameLogModel,
                batch_id=batch_id,
                source=str(operation.source),
                target=str(operation.target),
                media_type=operation.media_type,
                status="applied",
            )
        remove_empty_source_dirs(applied)
        await refresh_after_rename(db, parsed, applied)
        await update_job(
            db,
            job_id,
            status="done",
            progress=100,
            title="Rename complete",
            message=f"Renamed {len(applied)} file(s)",
            detail=f"Batch {batch_id}",
            result=json.dumps({"affected": len(applied), "batch_id": batch_id}),
        )
    except Exception as exc:  # noqa: BLE001 - persist job-level failure
        await update_job(
            db,
            job_id,
            status="error",
            progress=100,
            title="Rename failed",
            message=str(exc),
            error=str(exc),
        )


async def refresh_after_rename(
    db: AsyncDBClient,
    parsed_items: list[ParsedMediaFile],
    applied: list[RenameOperation],
) -> None:
    primary_by_source = {item.path.expanduser().resolve(): item for item in parsed_items}
    context = OrganizerScanContext.create()
    fallback_items = []
    now = dt.datetime.now()
    for operation in applied:
        source = operation.source.expanduser().resolve()
        original = primary_by_source.get(source)
        if original is None:
            continue
        refreshed = parse_media_filename(operation.target) or replace(
            original,
            path=operation.target,
        )
        item = _light_item_from_parsed(refreshed, context)
        payload = item.model_dump(mode="json")
        payload["is_new"] = False
        await delete_conflicting_target_row(db, source=str(source), target=item.path)
        affected = await db.objects.execute(
            OrganizerMediaModel.update(
                path=item.path,
                source_kind=source_kind_for_item(item),
                media_type=item.media_type,
                title=item.title,
                artist=item.artist,
                album=item.album,
                year=item.year,
                season=item.season,
                episode=item.episode,
                disc=item.disc,
                track=item.track,
                parse_template=item.parse_template,
                parse_relative_path=item.parse_relative_path,
                confidence=item.confidence,
                is_new=0,
                has_metadata=1 if item.metadata else 0,
                has_images=1 if item.images else 0,
                has_subtitles=1 if item.subtitles else 0,
                has_lyrics=1 if item.lyrics else 0,
                payload=json.dumps(payload, ensure_ascii=False),
                missing=0,
                last_seen_at=now,
            ).where(OrganizerMediaModel.path == str(source))
        )
        if not affected:
            fallback_items.append(item)
    if fallback_items:
        await persist_scan_items(db, fallback_items, mark_missing=False)


async def delete_conflicting_target_row(db: AsyncDBClient, *, source: str, target: str) -> None:
    if source == target:
        return
    source_rows = await db.objects.fetchall(
        OrganizerMediaModel.select(OrganizerMediaModel.id)
        .where(OrganizerMediaModel.path == source)
        .limit(1)
    )
    if not source_rows:
        return
    await db.objects.execute(
        OrganizerMediaModel.delete().where(
            (OrganizerMediaModel.path == target)
            & (OrganizerMediaModel.path != source)
        )
    )
