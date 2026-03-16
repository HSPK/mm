"""uom import — import media files into a library directory.

Scans the source, organises files into the destination using a template,
and stores the database (uom.db) inside the destination directory.
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from uom.cli import Context, pass_ctx
from uom.config import DEFAULT_DB_NAME, DEFAULT_IMPORT_TEMPLATE, resolve_media_path


@click.command("import")
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("destination", type=click.Path(path_type=Path))
@click.option(
    "--template",
    "-t",
    default=None,
    help="Path template.  Variables: {year}, {month}, {day}, {camera}, {type}, {ext}, {original_name}, {tags}. "
    "If omitted, uses the template stored in the library DB (default: "
    + DEFAULT_IMPORT_TEMPLATE
    + ").",
)
@click.option("--move", is_flag=True, help="Move files instead of copying.")
@click.option(
    "--dry-run/--no-dry-run", default=True, show_default=True, help="Preview without executing."
)
@pass_ctx
def import_cmd(
    ctx: Context,
    source: Path,
    destination: Path,
    template: str | None,
    move: bool,
    dry_run: bool,
) -> None:
    """Import media files into a library directory.

    Scans SOURCE for media, organises files into DESTINATION using a
    template, and stores the library database inside DESTINATION.
    """
    from uom.core.importer import execute_import, plan_import

    # Use DB in the destination directory
    dest = destination.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    db_path = dest / DEFAULT_DB_NAME

    # Re-initialise repo pointing at the destination DB
    from uom.db.sync_repo import SyncRepo

    repo = SyncRepo(db_path)
    click.echo(f"Library database: {db_path}")

    # Resolve template: CLI flag > DB stored value > default
    if template is None:
        stored = repo.get_config("import_template")
        template = stored if stored else DEFAULT_IMPORT_TEMPLATE
        click.echo(f"Using stored template: {template}")
    else:
        # Save the explicitly provided template to the DB for future imports
        repo.set_config("import_template", template)
        click.echo(f"Template saved to library: {template}")

    # library_root = destination directory (where the DB lives)
    library_root = dest

    # If the destination DB has no media yet, scan the source first
    all_media = repo.all_media()
    src_str = str(source.resolve())

    def _matches_source(m_path: str) -> bool:
        """Check if a stored path (relative or absolute) belongs to source."""
        if os.path.isabs(m_path):
            return m_path.startswith(src_str)
        abs_path = os.path.normpath(os.path.join(str(library_root), m_path))
        return abs_path.startswith(src_str)

    media_under_src = [m for m in all_media if _matches_source(m.path)]

    if not media_under_src:
        click.echo(f"No media in DB for {source}. Scanning source first...")
        from uom.cli._utils import parallel_scan, print_scan_summary
        from uom.core.scanner import discover_media, save_scan_result

        files = list(discover_media(source))
        click.echo(f"Found {len(files)} media file(s).")

        if files:
            results, _errors = parallel_scan(files, label="Scanning")
            for result in results:
                save_scan_result(repo, result, library_root=library_root)
            print_scan_summary(results, _errors)

        # Refresh
        all_media = repo.all_media()
        media_under_src = [m for m in all_media if _matches_source(m.path)]

    if not media_under_src:
        click.echo("No media found. Nothing to import.")
        return

    click.echo(f"Planning import for {len(media_under_src)} file(s)...")
    click.echo(f"Template: {template}")
    click.echo(f"Destination: {dest}\n")

    triplets = []
    for m in media_under_src:
        m.path = resolve_media_path(m.path, str(library_root))
        md = repo.get_metadata(m.id) if m.id else None  # type: ignore[arg-type]
        tags_info = repo.tags_for_media(m.id) if m.id else []  # type: ignore[arg-type]
        tag_names = [t.name for t, _ in tags_info]
        triplets.append((m, md, tag_names))

    actions = plan_import(triplets, dest, template)

    skipped = [a for a in actions if a.skipped]
    pending = [a for a in actions if not a.skipped]

    click.echo(f"  {len(pending)} to {'move' if move else 'copy'}, {len(skipped)} skipped\n")

    if dry_run:
        for a in pending[:20]:
            click.echo(f"  {a.source}")
            click.echo(f"    → {a.destination}\n")
        if len(pending) > 20:
            click.echo(f"  ... and {len(pending) - 20} more\n")
        click.echo("Dry-run — no files changed. Use --no-dry-run to execute.")
    else:
        label = "Moving files" if move else "Copying files"
        bar = click.progressbar(length=len(pending), label=label)
        with bar:

            def _progress(current: int, total: int) -> None:
                bar.update(1)

            count = execute_import(actions, move=move, on_progress=_progress)
        click.echo(f"\nDone. {'Moved' if move else 'Copied'} {count} file(s).")
        click.echo(f"Library DB saved at: {db_path}")
