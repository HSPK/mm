from __future__ import annotations

import click

from mm.cli import ui
from mm.cli.db import db
from mm.io import local_storage


@db.command("clean")
@click.option("--dry-run", is_flag=True, help="Only show what would be removed.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def db_clean(dry_run: bool, yes: bool) -> None:
    """Remove database entries whose files no longer exist on disk, and clean orphan rows."""
    from mm.cli import active_library
    from mm.library.maintenance import (
        cleanup_orphan_rows,
        delete_missing_media,
        plan_missing_media_cleanup,
    )

    active = active_library()
    db = active.db
    library_root = str(active.config.library_root)
    plan = plan_missing_media_cleanup(db, library_root, storage=local_storage)
    ui.info(f"Checking {plan.total_records:,} records ...")

    if plan.missing_ids:
        ui.warning(f"Found {len(plan.missing_ids):,} record(s) with missing files.")
        ui.bullet_list("Missing Files", plan.missing_paths, limit=20)

        if dry_run:
            ui.info("(dry-run) No changes made.")
            return

        if not yes:
            ui.confirm(
                f"Delete {len(plan.missing_ids)} record(s) from database? This cannot be undone.",
                abort=True,
            )

        deleted = delete_missing_media(db, plan.missing_ids)
        ui.success(f"Deleted {deleted:,} media record(s).")
    else:
        ui.success("All media records are valid.")

    orphan = cleanup_orphan_rows(db)
    if orphan.metadata:
        ui.success(f"Removed {orphan.metadata:,} orphan metadata row(s).")
    if orphan.media_tags:
        ui.success(f"Removed {orphan.media_tags:,} orphan media-tag row(s).")
    if orphan.tags:
        ui.success(f"Removed {orphan.tags:,} orphan tag(s).")
