from __future__ import annotations

import os
from pathlib import Path

import click

from mm.cli.db import db
from mm.config import resolve_media_path


@db.command("sync")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def db_sync(directory: Path, jobs: int, yes: bool) -> None:
    """Sync database with disk: remove stale entries and re-scan changed files.

    This is equivalent to running `db clean` followed by `scan` for the
    given directory, but it also detects files that moved or changed size.
    """
    from mm.cli import get_db_path, get_repo

    repo = get_repo()
    root = str(directory.resolve())
    library_root = str(get_db_path().resolve().parent)

    # ---- Phase 1: find stale records under this directory ----
    all_rows = repo.all_media_paths()
    stale_ids: list[int] = []
    stale_paths: list[str] = []
    changed_ids: list[int] = []
    changed_paths: list[str] = []

    for mid, path in all_rows:
        abs_path = resolve_media_path(path, library_root)
        if not abs_path.startswith(root):
            continue
        if not os.path.exists(abs_path):
            stale_ids.append(mid)
            stale_paths.append(abs_path)
        else:
            # Check if file size changed since last scan
            media = repo.get_media_by_id(mid)
            if media and media.file_size != os.path.getsize(abs_path):
                changed_ids.append(mid)
                changed_paths.append(abs_path)

    click.echo(f"Directory : {root}")
    click.echo(
        f"DB records: {sum(1 for _, p in all_rows if resolve_media_path(p, library_root).startswith(root))}"
    )
    click.echo(f"Stale     : {len(stale_ids)}")
    click.echo(f"Changed   : {len(changed_ids)}")

    if not stale_ids and not changed_ids:
        click.echo("Everything is in sync — nothing to do.")
        return

    # Show details
    if stale_paths:
        click.echo("\nMissing files (will be removed from DB):")
        for p in stale_paths[:10]:
            click.echo(f"  ✗ {p}")
        if len(stale_paths) > 10:
            click.echo(f"  ... and {len(stale_paths) - 10} more")

    if changed_paths:
        click.echo("\nChanged files (will be re-scanned):")
        for p in changed_paths[:10]:
            click.echo(f"  ↻ {p}")
        if len(changed_paths) > 10:
            click.echo(f"  ... and {len(changed_paths) - 10} more")

    if not yes:
        click.confirm(
            click.style(
                f"⚠  Delete {len(stale_ids)} stale record(s) and re-scan {len(changed_ids)} file(s)?",
                fg="yellow",
            ),
            abort=True,
        )

    # ---- Phase 2: delete stale records ----
    if stale_ids:
        deleted = repo.bulk_delete_media(stale_ids)
        orphan_tags = repo.delete_orphan_tags()
        click.echo(f"Deleted {deleted} stale record(s).")
        if orphan_tags:
            click.echo(f"Removed {orphan_tags} orphan tag(s).")

    # ---- Phase 3: re-scan changed files ----
    if changed_ids:
        from mm.cli._utils import parallel_scan
        from mm.core.scanner import save_scan_result

        # Delete old records so they'll be re-inserted fresh
        repo.bulk_delete_media(changed_ids)

        click.echo(f"\nRe-scanning {len(changed_paths)} file(s)...")
        results, errors = parallel_scan(
            [Path(p) for p in changed_paths], jobs=jobs, label="Scanning"
        )

        for r in results:
            save_scan_result(repo, r)

        click.echo(f"Re-scanned {len(results)} file(s).{f' {errors} error(s).' if errors else ''}")
