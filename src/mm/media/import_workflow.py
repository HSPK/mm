"""High-level media import workflow helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mm.db.sync_client import DBClient
from mm.io import FileStorage
from mm.media.importer import ImportPlanItem, execute_import, plan_import
from mm.media.scanner import ScanResult, save_media_metadata
from mm.utils.hashing import file_hash
from mm.utils.parallel import MapBackend, map_items


def _hash_path(item: tuple[Path, FileStorage]) -> tuple[str, Path]:
    path, storage = item
    return file_hash(path, storage=storage), path


@dataclass(frozen=True)
class HashDedupResult:
    files: list[Path]
    new_files: list[Path]
    intra_duplicates: int
    library_duplicates: int


def hash_and_dedup_files(
    db: DBClient,
    files: list[Path],
    *,
    storage: FileStorage,
    backend: MapBackend = "thread",
    on_file_hashed: Callable[[Path], None] | None = None,
) -> HashDedupResult:
    """Hash discovered files and keep only candidates not already in the library."""
    file_hashes: dict[str, Path] = {}
    for digest, path in map_items(
        _hash_path,
        [(path, storage) for path in files],
        backend=backend,
        on_result=lambda result: on_file_hashed(result[1]) if on_file_hashed else None,
    ):
        file_hashes.setdefault(digest, path)

    known = db.media.existing_hashes(list(file_hashes.keys()))
    new_files = [path for digest, path in file_hashes.items() if digest not in known]
    return HashDedupResult(
        files=files,
        new_files=new_files,
        intra_duplicates=len(files) - len(file_hashes),
        library_duplicates=len(file_hashes) - len(new_files),
    )


def build_import_plan(
    results: list[ScanResult],
    library_root: Path,
    template: str,
    *,
    storage: FileStorage,
) -> list[ImportPlanItem]:
    """Build file operation actions from scanned media results."""
    media_items = [(result.media, result.metadata) for result in results]
    return plan_import(media_items, library_root, template, storage=storage)


def execute_import_plan(
    db: DBClient,
    plan: list[ImportPlanItem],
    *,
    move: bool = False,
    storage: FileStorage,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Execute an import plan and store imported destination paths in the DB."""
    count = execute_import(plan, move=move, on_progress=on_progress, storage=storage)
    for item in plan:
        if not item.skipped:
            save_media_metadata(db, item.media, item.metadata, media_path=item.destination)
    return count
