#!/usr/bin/env python3
"""Repair media paths saved from import sources instead of copied destinations."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import click

from mm.cli import ui
from mm.config import DEFAULT_IMPORT_TEMPLATE
from mm.db.sync_client import DBClient
from mm.errors import MMError
from mm.io import local_storage
from mm.utils.media_paths import (
    MediaPathRepairPlan,
    apply_media_path_repairs,
    delete_missing_media_rows,
    plan_media_path_repairs,
)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--db",
    "db_path",
    default=Path("mm.db"),
    type=click.Path(dir_okay=False, path_type=Path),
    show_default=True,
    help="SQLite database path.",
)
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    help="Write changes. Without this flag, only print a dry-run summary.",
)
@click.option(
    "--no-backup",
    is_flag=True,
    help="Do not create a timestamped .bak file before applying changes.",
)
@click.option(
    "--allow-unresolved",
    is_flag=True,
    help="Apply safe changes even when some existing bad paths cannot be matched.",
)
def main(
    db_path: Path,
    apply_changes: bool,
    no_backup: bool,
    allow_unresolved: bool,
) -> None:
    db_path = db_path.resolve()
    if not local_storage.exists(db_path):
        raise click.ClickException(f"DB not found: {db_path}")

    db = DBClient(db_path)
    try:
        config = db.library_config.get()
        library_root = config.library_root
        if not local_storage.exists(library_root):
            raise click.ClickException(f"library_root does not exist: {library_root}")

        try:
            plan = plan_media_path_repairs(
                db,
                library_root,
                config.import_template or DEFAULT_IMPORT_TEMPLATE,
                storage=local_storage,
            )
        except MMError as error:
            raise click.ClickException(error.message) from error
        _print_plan(db_path, plan)

        if not apply_changes:
            ui.info("Dry run only; rerun with --apply to update the database.")
            if plan.unresolved or plan.conflicts:
                raise SystemExit(1)
            return

        if plan.conflicts or (plan.unresolved and not allow_unresolved):
            raise click.ClickException(
                "refusing to apply because some paths could not be safely resolved"
            )

        if not plan.updates and not plan.deletions:
            ui.success("No changes to apply.")
            if plan.unresolved:
                raise SystemExit(1)
            return

        if not no_backup:
            backup = db_path.with_name(
                f"{db_path.name}.bak-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            local_storage.copy(db_path, backup)
            ui.key_values("Backup", [("Path", ui.path(backup))])

        updated = apply_media_path_repairs(db, plan.updates)
        deleted = delete_missing_media_rows(db, plan.deletions)
        ui.success(f"Updated rows: {updated:,}; deleted rows: {deleted:,}")
    finally:
        db.close()


def _print_plan(db_path: Path, plan: MediaPathRepairPlan) -> None:
    ui.key_values(
        "Path Repair",
        [
            ("Database", ui.path(db_path)),
            ("Library", ui.path(plan.library_root)),
            ("Media records", f"{plan.scanned:,}"),
            ("Candidate bad paths", f"{plan.bad_paths:,}"),
            ("Resolved", f"{len(plan.updates):,}"),
            ("To delete", f"{len(plan.deletions):,}"),
            ("Unresolved", f"{len(plan.unresolved):,}"),
            ("Path conflicts", f"{len(plan.conflicts):,}"),
        ],
    )

    if plan.by_method:
        ui.print_table(
            [ui.Column("Method"), ui.Column("Rows", justify="right")],
            [[method, f"{count:,}"] for method, count in sorted(plan.by_method.items())],
            title="Resolution Methods",
        )

    if plan.updates:
        ui.print_table(
            [
                ui.Column("ID", justify="right"),
                ui.Column("Old path", max_width=56),
                ui.Column("New path", max_width=56),
                ui.Column("Method"),
            ],
            [
                [item.media_id, item.old_path, item.new_path, item.method]
                for item in plan.updates[:10]
            ],
            title="Repair Preview",
            caption=(f"... and {len(plan.updates) - 10} more" if len(plan.updates) > 10 else None),
        )

    if plan.deletions:
        ui.print_table(
            [
                ui.Column("ID", justify="right"),
                ui.Column("Stored path", max_width=56),
                ui.Column("Resolved path", max_width=56),
                ui.Column("Reason"),
            ],
            [
                [item.media_id, item.path, item.resolved_path, item.reason]
                for item in plan.deletions[:10]
            ],
            title="Delete Preview",
            caption=(
                f"... and {len(plan.deletions) - 10} more" if len(plan.deletions) > 10 else None
            ),
        )

    if plan.unresolved:
        ui.print_table(
            [
                ui.Column("ID", justify="right"),
                ui.Column("Path", max_width=72),
                ui.Column("Reason"),
            ],
            [[item.media_id, item.path, item.reason] for item in plan.unresolved[:10]],
            title="Unresolved Samples",
            caption=(
                f"... and {len(plan.unresolved) - 10} more" if len(plan.unresolved) > 10 else None
            ),
        )

    if plan.conflicts:
        ui.print_table(
            [
                ui.Column("ID", justify="right"),
                ui.Column("Path", max_width=72),
                ui.Column("Owner", justify="right"),
            ],
            [[item.media_id, item.path, item.owner_id] for item in plan.conflicts[:10]],
            title="Conflict Samples",
            caption=(
                f"... and {len(plan.conflicts) - 10} more" if len(plan.conflicts) > 10 else None
            ),
        )


if __name__ == "__main__":
    main()
