"""uom organize — reorganise media files using templates."""

from __future__ import annotations

from pathlib import Path

import click

from uom.cli import Context, pass_ctx
from uom.config import DEFAULT_ORGANIZE_TEMPLATE


@click.command()
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("destination", type=click.Path(path_type=Path))
@click.option(
    "--template",
    "-t",
    default=DEFAULT_ORGANIZE_TEMPLATE,
    show_default=True,
    help="Path template.  Variables: {year}, {month}, {day}, {camera}, {type}, {ext}, {original_name}, {tags}.",
)
@click.option("--move", is_flag=True, help="Move files instead of copying.")
@click.option(
    "--dry-run/--no-dry-run", default=True, show_default=True, help="Preview without executing."
)
@pass_ctx
def organize(
    ctx: Context, source: Path, destination: Path, template: str, move: bool, dry_run: bool
) -> None:
    """Organise media files into a directory structure using a template."""
    from uom.core.organizer import execute_organize, plan_organize

    repo = ctx.repo

    # Gather media + metadata + tags
    all_media = repo.all_media()
    src_str = str(source.resolve())
    media_under_src = [m for m in all_media if m.path.startswith(src_str)]

    if not media_under_src:
        click.echo("No media found in database under this directory. Run 'uom scan' first.")
        return

    click.echo(f"Planning organisation for {len(media_under_src)} file(s)...")
    click.echo(f"Template: {template}")
    click.echo(f"Destination: {destination.resolve()}\n")

    triplets = []
    for m in media_under_src:
        md = repo.get_metadata(m.id) if m.id else None  # type: ignore[arg-type]
        tags_info = repo.tags_for_media(m.id) if m.id else []  # type: ignore[arg-type]
        tag_names = [t.name for t, _ in tags_info]
        triplets.append((m, md, tag_names))

    actions = plan_organize(triplets, destination, template)

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
        count = execute_organize(actions, move=move)
        click.echo(f"\nDone. {'Moved' if move else 'Copied'} {count} file(s).")
