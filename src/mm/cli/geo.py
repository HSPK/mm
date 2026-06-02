from __future__ import annotations

import click

from mm.cli import ui


@click.group()
def geo() -> None:
    """Manage location data."""


@geo.command()
@click.option(
    "--reparse",
    is_flag=True,
    help="Re-geocode ALL items with GPS, including already labelled ones.",
)
def update(reparse: bool) -> None:
    """Update location for media files with GPS data (offline, no network needed)."""
    from mm.cli import active_library
    from mm.geo.updater import update_location_labels

    db = active_library().db

    candidates = db.metadata.needing_geo(force_reparse=reparse)
    if not candidates:
        ui.success("No items found needing location update.")
        return

    valid_count = sum(1 for md in candidates if md.gps_lat and md.gps_lon)
    if not valid_count:
        ui.warning("No items with valid GPS coordinates.")
        return

    ui.info(f"Geocoding {valid_count:,} items (offline)...")

    with ui.status("Resolving coordinates..."):
        with ui.progress("Updating locations", valid_count) as bar:
            result = update_location_labels(
                db,
                reparse=reparse,
                on_progress=lambda _row: bar.advance(),
            )

    ui.key_values(
        "Geocoding",
        [("Coordinates", f"{result.valid:,}"), ("Elapsed", f"{result.elapsed:.2f}s")],
    )

    ui.print_table(
        [
            ui.Column("ID", justify="right"),
            ui.Column("GPS"),
            ui.Column("Location", max_width=48),
            ui.Column("Country"),
            ui.Column("City"),
        ],
        [
            [str(row.metadata_id), row.gps, row.location, row.country, row.city]
            for row in result.rows
        ],
        title="Location Updates",
    )
    ui.success(f"Updated {result.updated:,} / {result.valid:,} items.")
