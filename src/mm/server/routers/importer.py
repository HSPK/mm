from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from mm.db.dto import User
from mm.db.sync_client import DBClient
from mm.errors import MMError
from mm.extractor.metadata import (
    MetadataToolUnavailable,
    normalize_metadata_mode,
    require_metadata_mode,
)
from mm.io import local_storage
from mm.media.import_workflow import (
    build_import_plan,
    execute_import_plan,
    hash_and_dedup_files,
)
from mm.media.scanner import discover_media, scan_files
from mm.server.dependencies import get_current_user
from mm.server.utility_schemas import (
    ImportApplyResponse,
    ImportPlanBody,
    ImportPlanOperation,
    ImportPlanResponse,
)

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/plan", response_model=ImportPlanResponse)
async def import_plan(
    body: ImportPlanBody,
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> ImportPlanResponse:
    return await run_in_threadpool(_plan_import_sync, request.app.state.db_path, body)


@router.post("/apply", response_model=ImportApplyResponse)
async def import_apply(
    body: ImportPlanBody,
    request: Request,
    _u: User | None = Depends(get_current_user),
) -> ImportApplyResponse:
    result = await run_in_threadpool(_apply_import_sync, request.app.state.db_path, body)
    return ImportApplyResponse(
        file_count=result.file_count,
        indexed_count=result.indexed_count,
        message=f"Imported {result.file_count} file(s); indexed {result.indexed_count}.",
    )


def _plan_import_sync(db_path: str | Path, body: ImportPlanBody) -> ImportPlanResponse:
    mode = _require_metadata_mode(body.metadata_mode)
    source = Path(body.source).expanduser().resolve()
    if not local_storage.is_dir(source):
        raise HTTPException(400, f"Source is not a directory: {source}")

    db = DBClient(db_path)
    try:
        config = db.library_config.get()
        files = list(discover_media(source, storage=local_storage))
        if not files:
            return ImportPlanResponse(
                source=str(source),
                library_root=str(config.library_root),
                template=config.import_template,
                discovered=0,
                new_files=0,
                intra_duplicates=0,
                library_duplicates=0,
                importable=0,
                errors=0,
                operations=[],
            )
        dedup = hash_and_dedup_files(db, files, storage=local_storage, backend="thread")
        results, errors = scan_files(
            dedup.new_files,
            storage=local_storage,
            backend="thread",
            metadata_mode=mode,
        )
        try:
            plan = build_import_plan(
                results,
                config.library_root,
                config.import_template,
                storage=local_storage,
            )
        except MMError as err:
            raise HTTPException(400, err.message) from err
        operations = [
            ImportPlanOperation(
                source=str(item.source),
                destination=str(item.destination),
                media_type=item.media.media_type.value,
                status="skipped" if item.skipped else "ready",
                reason=item.reason,
            )
            for item in plan
        ]
        return ImportPlanResponse(
            source=str(source),
            library_root=str(config.library_root),
            template=config.import_template,
            discovered=len(files),
            new_files=len(dedup.new_files),
            intra_duplicates=dedup.intra_duplicates,
            library_duplicates=dedup.library_duplicates,
            importable=sum(1 for item in plan if not item.skipped),
            errors=errors,
            operations=operations,
        )
    finally:
        db.close()


def _apply_import_sync(db_path: str | Path, body: ImportPlanBody):
    mode = _require_metadata_mode(body.metadata_mode)
    source = Path(body.source).expanduser().resolve()
    if not local_storage.is_dir(source):
        raise HTTPException(400, f"Source is not a directory: {source}")

    db = DBClient(db_path)
    try:
        config = db.library_config.get()
        files = list(discover_media(source, storage=local_storage))
        dedup = hash_and_dedup_files(db, files, storage=local_storage, backend="thread")
        results, _errors = scan_files(
            dedup.new_files,
            storage=local_storage,
            backend="thread",
            metadata_mode=mode,
        )
        plan = build_import_plan(
            results,
            config.library_root,
            config.import_template,
            storage=local_storage,
        )
        return execute_import_plan(db, plan, move=body.move, storage=local_storage)
    finally:
        db.close()


def _require_metadata_mode(raw: str) -> str:
    try:
        mode = normalize_metadata_mode(raw)
        require_metadata_mode(mode)
        return mode
    except (ValueError, MetadataToolUnavailable) as err:
        raise HTTPException(400, str(err)) from err
