from __future__ import annotations

from mm.cli import ui
from mm.cli.db import db
from mm.utils.formatting import fmt_duration as _dur
from mm.utils.formatting import fmt_size as _sz


@db.command("stats")
def db_stats() -> None:
    """Show detailed database statistics."""
    from mm.cli import active_library

    active = active_library()
    db = active.db

    ov = db.stats.overview()
    comp = db.stats.completeness()
    years = db.stats.by_year()
    cams = db.stats.by_camera()
    exts = db.stats.by_extension()
    ratings = db.stats.ratings()
    tags = db.stats.top_tags(15)
    total = comp["total"]

    ui.section("Library Statistics")
    ui.key_values(
        "Library Overview",
        [
            ("Database", ui.path(active.database)),
            ("Date Range", f"{ov['earliest'] or '?'} → {ov['latest'] or '?'}"),
            ("Total Files", f"{ov['total']:,}"),
            ("Photos", f"{ov['photos']:,}"),
            ("Videos", f"{ov['videos']:,}"),
            ("Total Size", _sz(ov["total_size"])),
            ("Photo Size", _sz(ov["photo_size"])),
            ("Video Size", _sz(ov["video_size"])),
            ("Video Duration", _dur(ov["video_duration"]) if ov["video_duration"] else "-"),
            ("Tags", f"{ov['tags']:,}"),
            ("Albums", f"{ov['albums']:,}"),
        ],
    )

    ui.print_table(
        [
            ui.Column("Field"),
            ui.Column("Has", justify="right"),
            ui.Column("Missing", justify="right"),
            ui.Column("Coverage", justify="right"),
            ui.Column(""),
        ],
        [
            [
                "Date Taken",
                f"{comp['has_date']:,}",
                f"{comp['missing_date']:,}",
                ui.percent(comp["has_date"], total),
                ui.ratio_bar(comp["has_date"], total),
            ],
            [
                "GPS",
                f"{comp['has_gps']:,}",
                f"{comp['missing_gps']:,}",
                ui.percent(comp["has_gps"], total),
                ui.ratio_bar(comp["has_gps"], total),
            ],
            [
                "Location Name",
                f"{comp['has_location_label']:,}",
                f"{comp['missing_location_label']:,}",
                ui.percent(comp["has_location_label"], total),
                ui.ratio_bar(comp["has_location_label"], total),
            ],
            [
                "Camera",
                f"{comp['has_camera']:,}",
                f"{comp['missing_camera']:,}",
                ui.percent(comp["has_camera"], total),
                ui.ratio_bar(comp["has_camera"], total),
            ],
            [
                "Tags",
                f"{comp['has_tags']:,}",
                f"{comp['missing_tags']:,}",
                ui.percent(comp["has_tags"], total),
                ui.ratio_bar(comp["has_tags"], total),
            ],
        ],
        title="Metadata Completeness",
    )

    if years:
        max_year_total = max(y["total"] for y in years)
        ui.print_table(
            [
                ui.Column("Year"),
                ui.Column("Photos", justify="right"),
                ui.Column("Videos", justify="right"),
                ui.Column("Total", justify="right"),
                ui.Column("Size", justify="right"),
                ui.Column(""),
            ],
            [
                [
                    y["year"],
                    f"{y['photos']:,}",
                    f"{y['videos']:,}",
                    f"{y['total']:,}",
                    _sz(y["size"]),
                    ui.ratio_bar(y["total"], max_year_total),
                ]
                for y in years
            ],
            title="By Year",
        )

    if cams:
        ui.print_table(
            [
                ui.Column("Camera", max_width=42),
                ui.Column("Photos", justify="right"),
                ui.Column("Videos", justify="right"),
                ui.Column("Total", justify="right"),
                ui.Column("Size", justify="right"),
            ],
            [
                [
                    c["camera"],
                    f"{c['photos']:,}",
                    f"{c['videos']:,}",
                    f"{c['total']:,}",
                    _sz(c["size"]),
                ]
                for c in cams
            ],
            title="By Camera",
        )

    if exts:
        max_ext_count = max(e["count"] for e in exts)
        ui.print_table(
            [
                ui.Column("Extension"),
                ui.Column("Count", justify="right"),
                ui.Column("Size", justify="right"),
                ui.Column(""),
            ],
            [
                [
                    e["ext"],
                    f"{e['count']:,}",
                    _sz(e["size"]),
                    ui.ratio_bar(e["count"], max_ext_count),
                ]
                for e in exts
            ],
            title="By Format",
        )

    if ratings:
        stars_map = {0: "Unrated", 1: "★", 2: "★★", 3: "★★★", 4: "★★★★", 5: "★★★★★"}
        ui.print_table(
            [
                ui.Column("Rating"),
                ui.Column("Count", justify="right"),
                ui.Column("%", justify="right"),
                ui.Column(""),
            ],
            [
                [
                    stars_map.get(r["rating"], str(r["rating"])),
                    f"{r['count']:,}",
                    ui.percent(r["count"], total),
                    ui.ratio_bar(r["count"], total),
                ]
                for r in ratings
            ],
            title="Ratings",
        )

    if tags:
        max_tag_count = max(tg["count"] for tg in tags)
        ui.print_table(
            [
                ui.Column("Tag", max_width=32),
                ui.Column("Source"),
                ui.Column("Count", justify="right"),
                ui.Column(""),
            ],
            [
                [
                    tg["tag"],
                    tg["source"],
                    f"{tg['count']:,}",
                    ui.ratio_bar(tg["count"], max_tag_count),
                ]
                for tg in tags
            ],
            title="Top Tags",
        )

    ui.blank()
