from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui
from mm.errors import MMError
from mm.io import local_storage
from mm.media.scanner import scan_files


@click.command("import")
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--move", is_flag=True, help="Move files instead of copying.")
def import_cmd(source: Path, move: bool) -> None:
    """Import media files from SOURCE into the active library."""
    from mm.cli import active_library
    from mm.cli._utils import print_scan_summary
    from mm.media.import_workflow import (
        build_import_plan,
        execute_import_plan,
        hash_and_dedup_files,
    )
    from mm.media.scanner import discover_media

    active = active_library()
    db = active.db
    config = active.config
    library_root = config.library_root
    template = config.import_template
    ui.key_values(
        "Import Target",
        [("Library", ui.path(library_root)), ("Template", template)],
    )

    files = list(discover_media(source, storage=local_storage))
    if not files:
        ui.warning("No media files found in source.")
        return
    ui.info(f"Found {len(files):,} media file(s) in {source}.")
    with ui.progress("Hashing files", len(files)) as bar:
        scan = hash_and_dedup_files(
            db,
            files,
            storage=local_storage,
            backend="thread",
            on_file_hashed=lambda _path: bar.advance(),
        )

    if scan.intra_duplicates:
        ui.warning(f"{scan.intra_duplicates:,} intra-source duplicate(s) removed.")

    ui.key_values(
        "Import Scan",
        [
            ("New files", f"{len(scan.new_files):,}"),
            ("Already in library", f"{scan.library_duplicates:,}"),
        ],
    )

    if not scan.new_files:
        ui.success("All files already in library. Nothing to import.")
        return

    with ui.progress("Scanning metadata", len(scan.new_files)) as bar:
        results, _errors = scan_files(
            scan.new_files,
            storage=local_storage,
            backend="process",
            on_error=lambda result: ui.warning(f"{result.media.path}: {result.error}", stderr=True),
            on_progress=lambda _result: bar.advance(),
        )
    print_scan_summary(results, _errors)

    if not results:
        ui.warning("No importable media after scanning. Nothing to do.")
        return

    try:
        plan = build_import_plan(results, library_root, template, storage=local_storage)
    except MMError as error:
        ui.error(error.message)
        if error.details:
            ui.key_values("Error Details", sorted(error.details.items()))
        raise SystemExit(1)

    pending = [item for item in plan if not item.skipped]
    if not pending:
        ui.success("Nothing to import.")
        return

    action = "move" if move else "copy"
    if not ui.confirm(f"{action.title()} {len(pending):,} file(s) into the library?"):
        ui.warning("Aborted.")
        return

    label = "Moving files" if move else "Copying files"
    with ui.progress(label, len(pending)) as bar:

        def _progress(*_: int) -> None:
            bar.advance()

        count = execute_import_plan(
            db,
            plan,
            move=move,
            storage=local_storage,
            on_progress=_progress,
        )
    ui.success(f"{'Moved' if move else 'Copied'} {count:,} file(s).")
