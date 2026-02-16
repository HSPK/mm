"""uom db — database management commands."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import click

from uom.cli import Context, pass_ctx


@click.group()
def db() -> None:
    """Database management."""


@db.command("init")
@pass_ctx
def db_init(ctx: Context) -> None:
    """Initialise (or upgrade) the database."""
    _ = ctx.repo  # triggers connect + init_db
    click.echo(f"Database ready: {ctx.db_path.resolve()}")


@db.command("stats")
@pass_ctx
def db_stats(ctx: Context) -> None:
    """Show database statistics."""
    repo = ctx.repo

    total = repo.count_media()
    size = repo.total_size()
    dist = repo.type_distribution()
    tag_count = len(repo.all_tags())

    click.echo(f"Database : {ctx.db_path.resolve()}")
    click.echo(f"Files    : {total}")
    click.echo(f"Size     : {size / 1024 / 1024 / 1024:.2f} GB")
    click.echo(f"Tags     : {tag_count}")
    click.echo()
    if dist:
        click.echo("Type distribution:")
        for mtype, cnt in sorted(dist.items()):
            click.echo(f"  {mtype:<10} {cnt:>8}")


@db.command("export")
@click.option(
    "--format", "fmt", type=click.Choice(["csv", "json"]), default="json", show_default=True
)
@click.option(
    "-o", "--output", type=click.Path(path_type=Path), help="Output file (default: stdout)."
)
@pass_ctx
def db_export(ctx: Context, fmt: str, output: Path | None) -> None:
    """Export media metadata."""
    repo = ctx.repo
    media_list = repo.all_media()

    rows = []
    for m in media_list:
        md = repo.get_metadata(m.id) if m.id else None  # type: ignore[arg-type]
        tags_info = repo.tags_for_media(m.id) if m.id else []  # type: ignore[arg-type]
        tag_names = [t.name for t, _ in tags_info]

        row = {
            "path": m.path,
            "filename": m.filename,
            "extension": m.extension,
            "media_type": m.media_type.value,
            "file_size": m.file_size,
            "file_hash": m.file_hash,
            "date_taken": md.date_taken.isoformat() if md and md.date_taken else "",
            "camera_make": md.camera_make if md else "",
            "camera_model": md.camera_model if md else "",
            "width": md.width if md else "",
            "height": md.height if md else "",
            "tags": ",".join(tag_names),
        }
        rows.append(row)

    fh = open(output, "w", newline="") if output else sys.stdout

    try:
        if fmt == "json":
            json.dump(rows, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        else:
            if rows:
                writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    finally:
        if output and fh is not sys.stdout:
            fh.close()

    if output:
        click.echo(f"Exported {len(rows)} record(s) to {output}")


@db.command("clean")
@click.option("--dry-run", is_flag=True, help="Only show what would be removed.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
@pass_ctx
def db_clean(ctx: Context, dry_run: bool, yes: bool) -> None:
    """Remove database entries whose files no longer exist on disk, and clean orphan rows."""
    repo = ctx.repo
    all_rows = repo.all_media_paths()
    click.echo(f"Checking {len(all_rows)} records ...")

    missing_ids: list[int] = []
    missing_paths: list[str] = []
    for mid, path in all_rows:
        if not os.path.exists(path):
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


@db.command("sync")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
@pass_ctx
def db_sync(ctx: Context, directory: Path, jobs: int, yes: bool) -> None:
    """Sync database with disk: remove stale entries and re-scan changed files.

    This is equivalent to running `db clean` followed by `scan` for the
    given directory, but it also detects files that moved or changed size.
    """
    repo = ctx.repo
    root = str(directory.resolve())

    # ---- Phase 1: find stale records under this directory ----
    all_rows = repo.all_media_paths()
    stale_ids: list[int] = []
    stale_paths: list[str] = []
    changed_ids: list[int] = []
    changed_paths: list[str] = []

    for mid, path in all_rows:
        if not path.startswith(root):
            continue
        if not os.path.exists(path):
            stale_ids.append(mid)
            stale_paths.append(path)
        else:
            # Check if file size changed since last scan
            media = repo.get_media_by_id(mid)
            if media and media.file_size != os.path.getsize(path):
                changed_ids.append(mid)
                changed_paths.append(path)

    click.echo(f"Directory : {root}")
    click.echo(f"DB records: {sum(1 for _, p in all_rows if p.startswith(root))}")
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
        import multiprocessing as _mp
        from concurrent.futures import ProcessPoolExecutor, as_completed

        from uom.core.scanner import ScanResult, process_pool_worker, save_scan_result

        # Delete old records so they'll be re-inserted fresh
        repo.bulk_delete_media(changed_ids)

        num_workers = jobs if jobs > 0 else min(_mp.cpu_count(), 8)
        work_items = [(p, True) for p in changed_paths]

        click.echo(f"\nRe-scanning {len(changed_paths)} file(s) with {num_workers} worker(s) ...")

        results: list[ScanResult] = []
        errors = 0
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            futures = {pool.submit(process_pool_worker, item): item for item in work_items}
            with click.progressbar(length=len(futures), label="Scanning") as bar:
                for future in as_completed(futures):
                    r = future.result()
                    if r.error:
                        errors += 1
                        click.echo(f"\n  [WARN] {r.path}: {r.error}", err=True)
                    else:
                        results.append(r)
                    bar.update(1)

        for r in results:
            save_scan_result(repo, r)

        click.echo(f"Re-scanned {len(results)} file(s).{f' {errors} error(s).' if errors else ''}")
