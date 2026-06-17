from __future__ import annotations

import click

from mm.cli import ui
from mm.cli.db import db
from mm.io import local_storage


@db.command("sync")
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
@click.option(
    "--metadata-mode",
    type=click.Choice(["exiftool", "pillow"]),
    default="exiftool",
    show_default=True,
    help="Metadata extraction mode. Pillow mode extracts basic photo metadata only.",
)
def db_sync(jobs: int, yes: bool, metadata_mode: str) -> None:
    """Sync database with disk: index new files, remove stale entries, and re-scan changes.

    Scans the library root, compares persisted file state, and preserves media
    rows when moved files can be matched by hash.
    """
    from mm.cli import active_library
    from mm.extractor.metadata import (
        MetadataToolUnavailable,
        normalize_metadata_mode,
        require_metadata_mode,
    )
    from mm.library.maintenance import execute_library_sync, plan_library_sync

    try:
        normalized_metadata_mode = normalize_metadata_mode(metadata_mode)
        require_metadata_mode(normalized_metadata_mode)
    except MetadataToolUnavailable as error:
        ui.error(str(error))
        raise SystemExit(1) from error

    active = active_library()
    try:
        db = active.db
        library_root = str(active.config.library_root)

        ui.info("Discovering library files and reading sync state...")
        with ui.progress("Planning sync", None) as bar:
            plan = plan_library_sync(
                db,
                library_root,
                storage=local_storage,
                jobs=jobs,
                on_progress=lambda checked, total: bar.update(completed=checked, total=total),
            )

        ui.key_values(
            "Sync Plan",
            [
                ("Library", ui.path(library_root)),
                ("DB records", f"{plan.total_records:,}"),
                ("Disk files", f"{plan.disk_files:,}"),
                ("Stale", f"{len(plan.stale_ids):,}"),
                ("Changed", f"{len(plan.changed_ids):,}"),
                ("New", f"{len(plan.new_paths):,}"),
                ("Metadata", normalized_metadata_mode),
            ],
        )

        if not plan.stale_ids and not plan.changed_ids and not plan.new_paths:
            ui.success("Everything is in sync — nothing to do.")
            return

        if plan.stale_paths:
            ui.bullet_list("Missing Files (will be removed from DB)", plan.stale_paths, limit=10)

        if plan.changed_paths:
            ui.bullet_list("Changed Files (will be re-scanned)", plan.changed_paths, limit=10)

        if plan.new_paths:
            ui.bullet_list("New Files (will be indexed)", plan.new_paths, limit=10)

        if not yes:
            ui.confirm(
                f"Delete {len(plan.stale_ids)} stale record(s), re-scan "
                f"{len(plan.changed_ids)} changed file(s), and index "
                f"{len(plan.new_paths)} new file(s)?",
                abort=True,
            )

        scan_total = len(plan.changed_paths) + len(plan.new_paths)
        if scan_total:
            progress = ui.make_progress()
            with progress:
                scan_task = progress.add_task("Scanning files", total=scan_total)
                metadata_task = progress.add_task("Reading metadata", total=scan_total)
                save_task = progress.add_task("Saving database", total=scan_total)
                sync = execute_library_sync(
                    db,
                    plan,
                    jobs=jobs,
                    storage=local_storage,
                    metadata_mode=normalized_metadata_mode,
                    on_scan_progress=lambda _result: progress.advance(scan_task),
                    on_metadata_progress=lambda count: progress.advance(metadata_task, count),
                    on_save_progress=lambda: progress.advance(save_task),
                    on_error=lambda result: ui.warning(
                        f"{result.media.path}: {result.error}", stderr=True
                    ),
                )
                metadata_total = max(0, scan_total - sync.errors)
                progress.update(metadata_task, completed=metadata_total, total=metadata_total)
                progress.update(save_task, completed=sync.indexed, total=sync.indexed)
        else:
            with ui.status("Applying database changes"):
                sync = execute_library_sync(
                    db,
                    plan,
                    jobs=jobs,
                    storage=local_storage,
                    metadata_mode=normalized_metadata_mode,
                )

        if sync.deleted:
            ui.success(f"Deleted {sync.deleted:,} stale record(s).")
        if sync.orphan_tags:
            ui.success(f"Removed {sync.orphan_tags:,} orphan tag(s).")
        if sync.moved:
            ui.success(f"Updated {sync.moved:,} moved file path(s).")
        if sync.indexed:
            ui.success(f"Indexed {sync.indexed:,} file(s).")
        if sync.errors:
            ui.warning(f"Completed with {sync.errors:,} scan error(s).")
        else:
            ui.success("Sync complete.")
    finally:
        active.close()
