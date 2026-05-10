from __future__ import annotations

import os
from pathlib import Path

import click

from mm.cli import ui
from mm.cli.db import db
from mm.config import resolve_media_path


@db.command("sync")
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def db_sync(jobs: int, yes: bool) -> None:
    """Sync database with disk: remove stale entries and re-scan changed files.

    Scans the entire library, detects missing files and files whose size
    has changed since last scan.
    """
    from mm.cli import get_library_root, get_repo

    repo = get_repo()
    library_root = str(get_library_root().resolve())

    # ---- Phase 1: find stale records ----
    all_rows = repo.all_media_paths()
    stale_ids: list[int] = []
    stale_paths: list[str] = []
    changed_ids: list[int] = []
    changed_paths: list[str] = []

    for mid, path in all_rows:
        abs_path = resolve_media_path(path, library_root)
        if not os.path.exists(abs_path):
            stale_ids.append(mid)
            stale_paths.append(abs_path)
        else:
            # Check if file size changed since last scan
            media = repo.get_media_by_id(mid)
            if media and media.file_size != os.path.getsize(abs_path):
                changed_ids.append(mid)
                changed_paths.append(abs_path)

    ui.key_values(
        "Sync Plan",
        [
            ("Library", ui.path(library_root)),
            ("DB records", f"{len(all_rows):,}"),
            ("Stale", f"{len(stale_ids):,}"),
            ("Changed", f"{len(changed_ids):,}"),
        ],
    )

    if not stale_ids and not changed_ids:
        ui.success("Everything is in sync — nothing to do.")
        return

    # Show details
    if stale_paths:
        ui.bullet_list("Missing Files (will be removed from DB)", stale_paths, limit=10)

    if changed_paths:
        ui.bullet_list("Changed Files (will be re-scanned)", changed_paths, limit=10)

    if not yes:
        ui.confirm(
            f"Delete {len(stale_ids)} stale record(s) and re-scan {len(changed_ids)} file(s)?",
            abort=True,
        )

    # ---- Phase 2: delete stale records ----
    if stale_ids:
        deleted = repo.bulk_delete_media(stale_ids)
        orphan_tags = repo.delete_orphan_tags()
        ui.success(f"Deleted {deleted:,} stale record(s).")
        if orphan_tags:
            ui.success(f"Removed {orphan_tags:,} orphan tag(s).")

    # ---- Phase 3: re-scan changed files ----
    if changed_ids:
        from mm.cli._utils import parallel_scan
        from mm.core.scanner import save_scan_result

        # Delete old records so they'll be re-inserted fresh
        repo.bulk_delete_media(changed_ids)

        ui.info(f"Re-scanning {len(changed_paths):,} file(s)...")
        results, errors = parallel_scan(
            [Path(p) for p in changed_paths], jobs=jobs, label="Scanning"
        )

        for r in results:
            save_scan_result(repo, r)

        if errors:
            ui.warning(f"Re-scanned {len(results):,} file(s); {errors:,} error(s).")
        else:
            ui.success(f"Re-scanned {len(results):,} file(s).")
