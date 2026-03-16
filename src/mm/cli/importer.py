from __future__ import annotations

from pathlib import Path

import click


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
    click.echo(f"Library: {library_root}")

    template = repo.get_config("import_template")
    click.echo(f"Template: {template}")

    # ── 1. Discover media files on disk ──────────────────────────
    files = list(discover_media(source))
    if not files:
        click.echo("No media files found in source.")
        return
    click.echo(f"Found {len(files)} media file(s) in {source}.")

    # ── 2. Hash source files ─────────────────────────────────────
    file_hashes: dict[str, Path] = {}  # hash -> path (dedupes within batch)
    with click.progressbar(files, label="Hashing files") as bar:
        for fpath in bar:
            fh = file_hash(fpath)
            file_hashes.setdefault(fh, fpath)

    intra_dups = len(files) - len(file_hashes)
    if intra_dups:
        click.echo(f"  {intra_dups} intra-source duplicate(s) removed.")

    # ── 3. Batch-check against DB ────────────────────────────────
    known = repo.hashes_exist(list(file_hashes.keys()))
    new_files = [p for h, p in file_hashes.items() if h not in known]
    dup_count = len(file_hashes) - len(new_files)

    click.echo(f"  {len(new_files)} new, {dup_count} already in library.")

    if not new_files:
        click.echo("All files already in library. Nothing to import.")
        return

    # ── 4. Scan metadata for new files ───────────────────────────
    results, _errors = parallel_scan(new_files, label="Scanning metadata")
    triplets = []
    for result in results:
        triplets.append((result.media, result.metadata, []))
    print_scan_summary(results, _errors)

    # ── 5. Build import plan ─────────────────────────────────────
    if not triplets:
        click.echo("No importable media after scanning. Nothing to do.")
        return

    actions = plan_import(triplets, library_root, template)
    pending = [a for a in actions if not a.skipped]
    skipped = [a for a in actions if a.skipped]

    click.echo(f"\n  {len(pending)} to {'move' if move else 'copy'}, {len(skipped)} skipped\n")

    # Preview
    for a in pending[:20]:
        click.echo(f"  {a.source}")
        click.echo(f"    → {a.destination}\n")
    if len(pending) > 20:
        click.echo(f"  ... and {len(pending) - 20} more\n")

    if not pending:
        click.echo("Nothing to import.")
        return

    if not click.confirm("Proceed?"):
        click.echo("Aborted.")
        return

    # ── 6. Execute: save to DB + copy/move files ─────────────────
    for result in results:
        save_scan_result(repo, result)

    label = "Moving files" if move else "Copying files"
    bar = click.progressbar(length=len(pending), label=label)
    with bar:

        def _progress(current: int, total: int) -> None:
            bar.update(1)

        count = execute_import(actions, move=move, on_progress=_progress)
    click.echo(f"\nDone. {'Moved' if move else 'Copied'} {count} file(s).")
