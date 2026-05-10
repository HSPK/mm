from __future__ import annotations

import os

import click

from mm.cli import ui
from mm.cli.db import db
from mm.config import resolve_media_path


@db.command("clean")
@click.option("--dry-run", is_flag=True, help="Only show what would be removed.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def db_clean(dry_run: bool, yes: bool) -> None:
    """Remove database entries whose files no longer exist on disk, and clean orphan rows."""
    from mm.cli import get_db_path, get_repo

    repo = get_repo()
    all_rows = repo.all_media_paths()
    ui.info(f"Checking {len(all_rows):,} records ...")

    library_root = str(get_db_path().resolve().parent)
    missing_ids: list[int] = []
    missing_paths: list[str] = []
    for mid, path in all_rows:
        abs_path = resolve_media_path(path, library_root)
        if not os.path.exists(abs_path):
            missing_ids.append(mid)
            missing_paths.append(path)

    if missing_ids:
        ui.warning(f"Found {len(missing_ids):,} record(s) with missing files.")
        ui.bullet_list("Missing Files", missing_paths, limit=20)

        if dry_run:
            ui.info("(dry-run) No changes made.")
            return

        if not yes:
            ui.confirm(
                f"Delete {len(missing_ids)} record(s) from database? This cannot be undone.",
                abort=True,
            )

        deleted = repo.bulk_delete_media(missing_ids)
        ui.success(f"Deleted {deleted:,} media record(s).")
    else:
        ui.success("All media records are valid.")

    # Always clean orphaned rows (metadata, tags, embeddings whose media was deleted)
    orphan_meta = repo.delete_orphan_metadata()
    orphan_media_tags = repo.delete_orphan_media_tags()
    orphan_embeddings = repo.delete_orphan_embeddings()
    orphan_tags = repo.delete_orphan_tags()
    if orphan_meta:
        ui.success(f"Removed {orphan_meta:,} orphan metadata row(s).")
    if orphan_media_tags:
        ui.success(f"Removed {orphan_media_tags:,} orphan media-tag row(s).")
    if orphan_embeddings:
        ui.success(f"Removed {orphan_embeddings:,} orphan embedding(s).")
    if orphan_tags:
        ui.success(f"Removed {orphan_tags:,} orphan tag(s).")
