"""uom db — database management commands."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import click

from uom.cli import Context, pass_ctx
from uom.config import resolve_media_path


@click.group(invoke_without_command=False)
@pass_ctx
def db(ctx: Context) -> None:
    """Database management."""
    click.echo(f"Database: {ctx.db_path.resolve()}")


@db.command("init")
@pass_ctx
def db_init(ctx: Context) -> None:
    """Initialise (or upgrade) the database."""
    _ = ctx.repo  # triggers connect + init_db
    click.echo(f"Database ready: {ctx.db_path.resolve()}")


@db.command("stats")
@pass_ctx
def db_stats(ctx: Context) -> None:
    """Show detailed database statistics."""
    import unicodedata

    repo = ctx.repo

    from uom.cli._utils import fmt_duration as _dur
    from uom.cli._utils import fmt_size as _sz

    # ── Helpers ───────────────────────────────────────────────

    def _pct(part: int, whole: int) -> str:
        if whole == 0:
            return "  -"
        return f"{part * 100 / whole:5.1f}%"

    def _bar(part: int, whole: int, width: int = 12) -> str:
        """A small ASCII bar for visual proportion."""
        if whole == 0:
            return "░" * width
        filled = round(part / whole * width)
        return "█" * filled + "░" * (width - filled)

    def _display_width(s: str) -> int:
        """Calculate display width accounting for CJK fullwidth chars."""
        w = 0
        for ch in s:
            cat = unicodedata.east_asian_width(ch)
            w += 2 if cat in ("W", "F") else 1
        return w

    def _pad(s: str, target: int, align: str = "left") -> str:
        """Pad string to target display width, CJK-aware."""
        dw = _display_width(s)
        pad = max(0, target - dw)
        if align == "right":
            return " " * pad + s
        return s + " " * pad

    _last_table_width: int = 0  # track for section sizing

    def _section(title: str, icon: str = "─") -> None:
        nonlocal _last_table_width
        w = max(_last_table_width, 56)
        title_display = f"{icon} {title}"
        pad = w - _display_width(title_display) - 2
        click.echo()
        click.secho(f"  ┌{'─' * w}┐", fg="cyan")
        click.secho(f"  │  {title_display}{' ' * pad}│", fg="cyan", bold=True)
        click.secho(f"  └{'─' * w}┘", fg="cyan")

    def _table(headers: list[str], rows: list[list[str]], sep: str = " │ ") -> None:
        """Pretty-print a boxed table with CJK-aware alignment."""
        nonlocal _last_table_width
        ncols = len(headers)
        widths = [_display_width(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row[:ncols]):
                widths[i] = max(widths[i], _display_width(cell))

        def _fmt_row(cells: list[str], is_header: bool = False) -> str:
            parts = []
            for i, cell in enumerate(cells[:ncols]):
                if i == 0:
                    parts.append(_pad(cell, widths[i], "left"))
                else:
                    parts.append(_pad(cell, widths[i], "right"))
            return sep.join(parts)

        total_w = sum(widths) + len(sep) * (ncols - 1)
        border = "─" * (total_w + 4)
        _last_table_width = total_w + 4

        click.secho(f"  ┌{border}┐", dim=True)
        hdr_str = _fmt_row(headers, is_header=True)
        click.echo("  │ ", nl=False)
        click.secho(f" {hdr_str} ", bold=True, nl=False)
        click.echo(" │")
        click.secho(f"  ├{border}┤", dim=True)
        for row in rows:
            row_str = _fmt_row(row)
            click.echo(f"  │  {row_str}  │")
        click.secho(f"  └{border}┘", dim=True)

    def _kv(label: str, value: str, label_w: int = 18, color: str | None = None) -> None:
        """Print a key-value line."""
        padded_label = _pad(label, label_w)
        w = max(_last_table_width, 56)
        content = f"{padded_label}{value}"
        pad = max(0, w - _display_width(content) - 2)
        if color:
            click.echo(f"  │  {padded_label}", nl=False)
            click.secho(value, fg=color, nl=False)
            click.echo(f"{' ' * pad}│")
        else:
            click.echo(f"  │  {content}{' ' * pad}│")

    def _kv_sep() -> None:
        w = max(_last_table_width, 56)
        click.secho(f"  ├{'─' * w}┤", dim=True)

    def _kv_top() -> None:
        w = max(_last_table_width, 56)
        click.secho(f"  ┌{'─' * w}┐", dim=True)

    def _kv_bot() -> None:
        w = max(_last_table_width, 56)
        click.secho(f"  └{'─' * w}┘", dim=True)

    # ── Gather data ───────────────────────────────────────────
    ov = repo.stats_overview()
    comp = repo.stats_completeness()
    years = repo.stats_by_year()
    cams = repo.stats_by_camera()
    exts = repo.stats_by_extension()
    ratings = repo.stats_ratings()
    tags = repo.stats_top_tags(15)
    t = comp["total"]

    # ── Overview ──────────────────────────────────────────────
    # Pre-calculate the overview box width from its longest content line
    _ov_lines = [
        f"{'Database':<18}{ctx.db_path.resolve()}",
        f"{'Date Range':<18}{ov['earliest'] or '?'}  →  {ov['latest'] or '?'}",
        f"{'Total Files':<18}{ov['total']:>10,}",
        f"{'Total Size':<18}{_sz(ov['total_size']):>10}",
    ]
    _last_table_width = max(max(_display_width(ln) for ln in _ov_lines) + 2, 56)

    _section("Library Overview", "📊")
    _kv_top()
    _kv("Database", str(ctx.db_path.resolve()))
    _kv("Date Range", f"{ov['earliest'] or '?'}  →  {ov['latest'] or '?'}")
    _kv_sep()
    _kv("Total Files", f"{ov['total']:>10,}")
    _kv("  Photos", f"{ov['photos']:>10,}", color="green")
    _kv("  Videos", f"{ov['videos']:>10,}", color="yellow")
    _kv_sep()
    _kv("Total Size", f"{_sz(ov['total_size']):>10}")
    _kv("  Photos", f"{_sz(ov['photo_size']):>10}", color="green")
    _kv("  Videos", f"{_sz(ov['video_size']):>10}", color="yellow")
    if ov["video_duration"]:
        _kv("Video Duration", f"{_dur(ov['video_duration']):>10}")
    _kv_sep()
    _kv("Tags", f"{ov['tags']:>10,}")
    _kv("Albums", f"{ov['albums']:>10,}")
    _kv("Embeddings", f"{ov['embeddings']:>10,}")
    _kv_bot()

    # ── Metadata Completeness ────────────────────────────────
    _section("Metadata Completeness", "✅")
    _table(
        ["Field", "Has", "Missing", "Coverage", ""],
        [
            [
                "Date Taken",
                f"{comp['has_date']:,}",
                f"{comp['missing_date']:,}",
                _pct(comp["has_date"], t),
                _bar(comp["has_date"], t),
            ],
            [
                "GPS",
                f"{comp['has_gps']:,}",
                f"{comp['missing_gps']:,}",
                _pct(comp["has_gps"], t),
                _bar(comp["has_gps"], t),
            ],
            [
                "Location Name",
                f"{comp['has_location_label']:,}",
                f"{comp['missing_location_label']:,}",
                _pct(comp["has_location_label"], t),
                _bar(comp["has_location_label"], t),
            ],
            [
                "Camera",
                f"{comp['has_camera']:,}",
                f"{comp['missing_camera']:,}",
                _pct(comp["has_camera"], t),
                _bar(comp["has_camera"], t),
            ],
            [
                "Embeddings",
                f"{comp['has_embeddings']:,}",
                f"{comp['missing_embeddings']:,}",
                _pct(comp["has_embeddings"], t),
                _bar(comp["has_embeddings"], t),
            ],
            [
                "Tags",
                f"{comp['has_tags']:,}",
                f"{comp['missing_tags']:,}",
                _pct(comp["has_tags"], t),
                _bar(comp["has_tags"], t),
            ],
        ],
    )

    # ── By Year ──────────────────────────────────────────────
    if years:
        max_year_total = max(y["total"] for y in years) if years else 1
        _section("By Year", "📅")
        _table(
            ["Year", "Photos", "Videos", "Total", "Size", ""],
            [
                [
                    y["year"],
                    f"{y['photos']:,}",
                    f"{y['videos']:,}",
                    f"{y['total']:,}",
                    _sz(y["size"]),
                    _bar(y["total"], max_year_total),
                ]
                for y in years
            ],
        )

    # ── By Camera ────────────────────────────────────────────
    if cams:
        _section("By Camera", "📷")
        _table(
            ["Camera", "Photos", "Videos", "Total", "Size"],
            [
                [
                    c["camera"][:40],
                    f"{c['photos']:,}",
                    f"{c['videos']:,}",
                    f"{c['total']:,}",
                    _sz(c["size"]),
                ]
                for c in cams
            ],
        )

    # ── By Format ────────────────────────────────────────────
    if exts:
        max_ext_cnt = max(e["count"] for e in exts) if exts else 1
        _section("By Format", "📁")
        _table(
            ["Extension", "Count", "Size", ""],
            [
                [e["ext"], f"{e['count']:,}", _sz(e["size"]), _bar(e["count"], max_ext_cnt)]
                for e in exts
            ],
        )

    # ── Ratings ──────────────────────────────────────────────
    if ratings:
        _section("Ratings", "⭐")
        stars_map = {0: "Unrated", 1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
        _table(
            ["Rating", "Count", "%", ""],
            [
                [
                    stars_map.get(r["rating"], str(r["rating"])),
                    f"{r['count']:,}",
                    _pct(r["count"], t),
                    _bar(r["count"], t),
                ]
                for r in ratings
            ],
        )

    # ── Top Tags ─────────────────────────────────────────────
    if tags:
        max_tag_cnt = max(tg["count"] for tg in tags) if tags else 1
        _section("Top Tags", "🏷️")
        _table(
            ["Tag", "Source", "Count", ""],
            [
                [tg["tag"][:30], tg["source"], f"{tg['count']:,}", _bar(tg["count"], max_tag_cnt)]
                for tg in tags
            ],
        )

    click.echo()


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

    library_root = str(ctx.db_path.resolve().parent)
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
    library_root = str(ctx.db_path.resolve().parent)

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
        from uom.cli._utils import parallel_scan
        from uom.core.scanner import save_scan_result

        # Delete old records so they'll be re-inserted fresh
        repo.bulk_delete_media(changed_ids)

        click.echo(f"\nRe-scanning {len(changed_paths)} file(s)...")
        results, errors = parallel_scan(
            [Path(p) for p in changed_paths], jobs=jobs, label="Scanning"
        )

        for r in results:
            save_scan_result(repo, r, library_root=library_root)

        click.echo(f"Re-scanned {len(results)} file(s).{f' {errors} error(s).' if errors else ''}")


@db.command("migrate-paths")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing.")
@pass_ctx
def db_migrate_paths(ctx: Context, dry_run: bool) -> None:
    """Convert absolute media paths to relative (based on library root).

    The library root is the parent directory of the database file.
    Only paths that are absolute AND start with the library root will be
    converted; all other rows are left untouched.
    """
    from uom.db.models import MediaModel

    repo = ctx.repo
    library_root = str(ctx.db_path.resolve().parent)
    all_rows = repo.all_media_paths()

    click.echo(f"Library root: {library_root}")
    click.echo(f"Total media : {len(all_rows)}")

    to_update: list[tuple[int, str, str]] = []  # (id, old_abs, new_rel)
    already_rel = 0
    outside = 0

    for mid, path in all_rows:
        if not os.path.isabs(path):
            already_rel += 1
            continue
        if not path.startswith(library_root):
            outside += 1
            continue
        rel = os.path.relpath(path, library_root)
        to_update.append((mid, path, rel))

    click.echo(f"Already relative : {already_rel}")
    click.echo(f"Outside lib root : {outside}")
    click.echo(f"To convert       : {len(to_update)}")

    if not to_update:
        click.echo("\nNothing to do.")
        return

    # Preview
    for mid, old, new in to_update[:10]:
        click.echo(f"  [{mid}] {old}")
        click.echo(f"      → {new}")
    if len(to_update) > 10:
        click.echo(f"  ... and {len(to_update) - 10} more")

    if dry_run:
        click.echo("\n(dry-run) No changes made.")
        return

    # Batch update
    converted = 0
    with repo._repo.manager.allow_sync():
        with click.progressbar(to_update, label="Migrating paths") as bar:
            for mid, _old, new in bar:
                MediaModel.update(path=new).where(MediaModel.id == mid).execute()
                converted += 1

    click.echo(f"\nDone. Converted {converted} path(s) to relative.")
