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
    """Sync database with disk: remove stale entries and re-scan changed files.

    Scans the entire library, detects missing files and files whose size
    has changed since last scan.
    """
    from mm.cli import active_library
    from mm.extractor.metadata import (
        MetadataToolUnavailable,
        normalize_metadata_mode,
        require_metadata_mode,
    )
    from mm.library.maintenance import delete_stale_media, plan_library_sync, rescan_changed_media

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

        plan = plan_library_sync(db, library_root, storage=local_storage)

        ui.key_values(
            "Sync Plan",
            [
                ("Library", ui.path(library_root)),
                ("DB records", f"{plan.total_records:,}"),
                ("Stale", f"{len(plan.stale_ids):,}"),
                ("Changed", f"{len(plan.changed_ids):,}"),
                ("Metadata", normalized_metadata_mode),
            ],
        )

        if not plan.stale_ids and not plan.changed_ids:
            ui.success("Everything is in sync — nothing to do.")
            return

        if plan.stale_paths:
            ui.bullet_list("Missing Files (will be removed from DB)", plan.stale_paths, limit=10)

        if plan.changed_paths:
            ui.bullet_list("Changed Files (will be re-scanned)", plan.changed_paths, limit=10)

        if not yes:
            ui.confirm(
                f"Delete {len(plan.stale_ids)} stale record(s) and re-scan "
                f"{len(plan.changed_ids)} file(s)?",
                abort=True,
            )

        if plan.stale_ids:
            deleted, orphan_tags = delete_stale_media(db, plan.stale_ids)
            ui.success(f"Deleted {deleted:,} stale record(s).")
            if orphan_tags:
                ui.success(f"Removed {orphan_tags:,} orphan tag(s).")

        if plan.changed_ids:
            ui.info(f"Re-scanning {len(plan.changed_paths):,} file(s)...")
            with ui.progress("Scanning", len(plan.changed_paths)) as bar:
                rescan = rescan_changed_media(
                    db,
                    plan.changed_ids,
                    plan.changed_paths,
                    jobs=jobs,
                    storage=local_storage,
                    metadata_mode=normalized_metadata_mode,
                    on_progress=lambda _result: bar.advance(),
                    on_error=lambda result: ui.warning(
                        f"{result.media.path}: {result.error}", stderr=True
                    ),
                )

            if rescan.errors:
                ui.warning(f"Re-scanned {rescan.scanned:,} file(s); {rescan.errors:,} error(s).")
            else:
                ui.success(f"Re-scanned {rescan.scanned:,} file(s).")
    finally:
        active.close()
