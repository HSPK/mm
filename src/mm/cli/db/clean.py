from __future__ import annotations

import os

import click

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
    click.echo(f"Checking {len(all_rows)} records ...")

    library_root = str(get_db_path().resolve().parent)
    missing_ids: list[int] = []
    missing_paths: list[str] = []
    for mid, path in all_rows:
        abs_path = resolve_media_path(path, library_root)
        if not os.path.exists(abs_path):
            missing_ids.append(mid)
            missing_paths.append(path)

    if missing_ids:
        click.echo(f"Found {len(missing_ids)} record(s) with missing files.")
        if len(missing_paths) <= 20:
            for p in missing_paths:
                click.echo(f"  ✗ {p}")
        else:
            for p in missing_paths[:10]:
                click.echo(f"  ✗ {p}")
            click.echo(f"  ... and {len(missing_paths) - 10} more")

        if dry_run:
            click.echo("(dry-run) No changes made.")
            return

        if not yes:
            click.confirm(
                click.style(
                    f"⚠  Delete {len(missing_ids)} record(s) from database? This cannot be undone.",
                    fg="yellow",
                ),
                abort=True,
            )

        deleted = repo.bulk_delete_media(missing_ids)
        click.echo(f"Deleted {deleted} media record(s).")
    else:
        click.echo("All media records are valid.")

    # Always clean orphaned rows (metadata, tags, embeddings whose media was deleted)
    orphan_meta = repo.delete_orphan_metadata()
    orphan_media_tags = repo.delete_orphan_media_tags()
    orphan_embeddings = repo.delete_orphan_embeddings()
    orphan_tags = repo.delete_orphan_tags()
    if orphan_meta:
        click.echo(f"Removed {orphan_meta} orphan metadata row(s).")
    if orphan_media_tags:
        click.echo(f"Removed {orphan_media_tags} orphan media-tag row(s).")
    if orphan_embeddings:
        click.echo(f"Removed {orphan_embeddings} orphan embedding(s).")
    if orphan_tags:
        click.echo(f"Removed {orphan_tags} orphan tag(s).")
