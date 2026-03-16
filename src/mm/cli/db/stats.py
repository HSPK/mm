from __future__ import annotations

import unicodedata

import click

from mm.cli._utils import fmt_duration as _dur
from mm.cli._utils import fmt_size as _sz
from mm.cli.db import db

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
    global _last_table_width
    w = max(_last_table_width, 56)
    title_display = f"{icon} {title}"
    pad = w - _display_width(title_display) - 2
    click.echo()
    click.secho(f"  ┌{'─' * w}┐", fg="cyan")
    click.secho(f"  │  {title_display}{' ' * pad}│", fg="cyan", bold=True)
    click.secho(f"  └{'─' * w}┘", fg="cyan")


def _table(headers: list[str], rows: list[list[str]], sep: str = " │ ") -> None:
    """Pretty-print a boxed table with CJK-aware alignment."""
    global _last_table_width
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


@db.command("stats")
def db_stats() -> None:
    """Show detailed database statistics."""
    from mm.cli import get_db_path, get_repo

    global _last_table_width

    db_path = get_db_path()
    repo = get_repo()

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
        f"{'Database':<18}{db_path.resolve()}",
        f"{'Date Range':<18}{ov['earliest'] or '?'}  →  {ov['latest'] or '?'}",
        f"{'Total Files':<18}{ov['total']:>10,}",
        f"{'Total Size':<18}{_sz(ov['total_size']):>10}",
    ]
    _last_table_width = max(max(_display_width(ln) for ln in _ov_lines) + 2, 56)

    _section("Library Overview", "📊")
    _kv_top()
    _kv("Database", str(db_path.resolve()))
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
                [
                    e["ext"],
                    f"{e['count']:,}",
                    _sz(e["size"]),
                    _bar(e["count"], max_ext_cnt),
                ]
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
                [
                    tg["tag"][:30],
                    tg["source"],
                    f"{tg['count']:,}",
                    _bar(tg["count"], max_tag_cnt),
                ]
                for tg in tags
            ],
        )

    click.echo()
