from __future__ import annotations

import click


@click.command()
def dedup() -> None:
    """Find and remove duplicate media files (by hash in the database)."""
    from mm.cli import get_library_root, get_repo
    from mm.core.dedup import find_duplicates

    repo = get_repo()
    root = get_library_root()
    click.echo("Searching for duplicates in the database...\n")

    groups = find_duplicates(repo)

    if not groups:
        click.echo("No duplicates found.")
        return

    total_dups = sum(len(g.duplicates) for g in groups)
    total_saved = 0
    for g in groups:
        for p in g.duplicates:
            try:
                total_saved += (root / p.path).stat().st_size
            except OSError:
                pass

    click.echo(
        f"Found {total_dups} duplicate(s) in {len(groups)} group(s), "
        f"can free {total_saved / 1024 / 1024:.1f} MB\n"
    )

    for g in groups:
        click.echo(f"  KEEP   : {g.keep.path}")
        for dup in g.duplicates:
            click.echo(f"  REMOVE : {dup.path}")
        click.echo()

    if click.confirm("Delete these duplicates?"):
        deleted = 0
        for g in groups:
            for dup in g.duplicates:
                try:
                    repo.delete_media(dup.id)
                    if (root / dup.path).exists():
                        (root / dup.path).unlink(missing_ok=True)
                        deleted += 1
                except OSError as e:
                    click.echo(f"  Error deleting {dup}: {e}", err=True)
        click.echo(f"\nDone. Removed {deleted} file(s), freed {total_saved / 1024 / 1024:.1f} MB.")
    else:
        click.echo("Aborted — no files deleted.")
