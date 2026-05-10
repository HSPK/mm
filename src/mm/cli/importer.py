from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui


@click.command("import")
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--move", is_flag=True, help="Move files instead of copying.")
def import_cmd(source: Path, move: bool) -> None:
    """Import media files from SOURCE into the active library."""
    from mm.cli import get_library_root, get_repo
    from mm.cli._utils import parallel_scan, print_scan_summary
    from mm.core.importer import execute_import, plan_import
    from mm.core.scanner import discover_media, file_hash, save_scan_result

    repo = get_repo()

    library_root = get_library_root()
    template = repo.get_config("import_template")
    ui.key_values(
        "Import Target",
        [("Library", ui.path(library_root)), ("Template", template)],
    )

    # ── 1. Discover media files on disk ──────────────────────────
    files = list(discover_media(source))
    if not files:
        ui.warning("No media files found in source.")
        return
    ui.info(f"Found {len(files):,} media file(s) in {source}.")

    # ── 2. Hash source files ─────────────────────────────────────
    file_hashes: dict[str, Path] = {}  # hash -> path (dedupes within batch)
    for fpath in ui.track(files, "Hashing files"):
        fh = file_hash(fpath)
        file_hashes.setdefault(fh, fpath)

    intra_dups = len(files) - len(file_hashes)
    if intra_dups:
        ui.warning(f"{intra_dups:,} intra-source duplicate(s) removed.")

    # ── 3. Batch-check against DB ────────────────────────────────
    known = repo.hashes_exist(list(file_hashes.keys()))
    new_files = [p for h, p in file_hashes.items() if h not in known]
    dup_count = len(file_hashes) - len(new_files)

    ui.key_values(
        "Import Scan",
        [
            ("New files", f"{len(new_files):,}"),
            ("Already in library", f"{dup_count:,}"),
        ],
    )

    if not new_files:
        ui.success("All files already in library. Nothing to import.")
        return

    # ── 4. Scan metadata for new files ───────────────────────────
    results, _errors = parallel_scan(new_files, label="Scanning metadata")
    triplets = []
    for result in results:
        triplets.append((result.media, result.metadata, []))
    print_scan_summary(results, _errors)

    # ── 5. Build import plan ─────────────────────────────────────
    if not triplets:
        ui.warning("No importable media after scanning. Nothing to do.")
        return

    actions = plan_import(triplets, library_root, template)
    pending = [a for a in actions if not a.skipped]
    skipped = [a for a in actions if a.skipped]

    action = "move" if move else "copy"
    ui.key_values(
        "Import Plan",
        [(f"To {action}", f"{len(pending):,}"), ("Skipped", f"{len(skipped):,}")],
    )

    # Preview
    preview = pending[:20]
    if preview:
        ui.print_table(
            [ui.Column("Source", max_width=56), ui.Column("Destination", max_width=56)],
            [[ui.path(a.source), ui.path(a.destination)] for a in preview],
            title="Import Preview",
            caption=f"... and {len(pending) - 20} more" if len(pending) > 20 else None,
        )

    if not pending:
        ui.success("Nothing to import.")
        return

    if not ui.confirm("Proceed?"):
        ui.warning("Aborted.")
        return

    # ── 6. Execute: save to DB + copy/move files ─────────────────
    for result in results:
        save_scan_result(repo, result)

    label = "Moving files" if move else "Copying files"
    with ui.progress(label, len(pending)) as bar:

        def _progress(current: int, total: int) -> None:
            bar.advance()

        count = execute_import(actions, move=move, on_progress=_progress)
    ui.success(f"{'Moved' if move else 'Copied'} {count:,} file(s).")
