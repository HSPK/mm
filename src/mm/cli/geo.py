from __future__ import annotations

import time

import click

from mm.core.geocoding import reverse_geocode_batch


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
    from mm.cli import get_repo

    repo = get_repo()

    items = repo.get_metadata_needing_geo_update(force_reparse=reparse)
    if not items:
        click.echo("No items found needing location update.")
        return

    # Filter items with valid GPS coordinates
    valid = [(md, md.gps_lat, md.gps_lon) for md in items if md.gps_lat and md.gps_lon]
    if not valid:
        click.echo("No items with valid GPS coordinates.")
        return

    click.echo(f"Geocoding {len(valid)} items (offline)...")
    t0 = time.perf_counter()

    # Batch geocode — single KD-tree query for all coordinates
    coords = [(lat, lon) for _, lat, lon in valid]
    results = reverse_geocode_batch(coords)

    elapsed = time.perf_counter() - t0
    click.echo(f"Geocoded {len(results)} coordinates in {elapsed:.2f}s")

    # Write results to DB
    count = 0
    for (md, lat, lon), (label, country, city) in zip(valid, results):
        if not label:
            click.echo(f"[{md.id}] No result for {lat:.4f},{lon:.4f}")
            continue
        try:
            repo.update_location_label(md.id, label, country=country, city=city)
            click.echo(f"[{md.id}] {lat:.4f},{lon:.4f} -> {label} ({country}, {city})")
            count += 1
        except Exception as e:
            click.echo(f"Error updating {md.id}: {e}")

    click.echo(f"Done. Updated {count} / {len(valid)} items.")
