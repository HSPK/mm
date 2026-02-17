"""uom geo — manage location metadata."""

from __future__ import annotations

import asyncio

import click

from uom.cli import Context, pass_ctx
from uom.core import geocoding


@click.group()
def geo() -> None:
    """Manage location data."""


@geo.command()
@click.option("--limit", type=int, default=1000, help="Max items to process.")
@click.option(
    "--reparse", is_flag=True, help="Reparse items that already have a label but missing details."
)
@pass_ctx
def update(ctx: Context, limit: int, reparse: bool) -> None:
    """Update location for media files with GPS data."""

    async def _process_geo_updates() -> None:
        from uom.db.async_repository import AsyncRepository

        repo = AsyncRepository(ctx.db_path)
        await repo.connect()
        await repo.init_db()

        items = await repo.get_metadata_needing_geo_update(limit=limit, force_reparse=reparse)
        if not items:
            click.echo("No items found needing location update.")
            return

        click.echo(f"Found {len(items)} items to geocode...")
        count = 0
        for md in items:
            lat, lon = md.gps_lat, md.gps_lon
            if lat is None or lon is None:
                continue
            try:
                label, country, city = await geocoding.reverse_geocode(lat, lon)
                if label:
                    await repo.update_location_label(md.id, label, country=country, city=city)
                    click.echo(f"[{md.id}] {lat:.4f},{lon:.4f} -> {label} ({country}, {city})")
                    count += 1
                else:
                    click.echo(f"[{md.id}] No result for {lat:.4f},{lon:.4f}")
                await asyncio.sleep(1.2)
            except Exception as e:
                click.echo(f"Error processing {md.id}: {e}")

        click.echo(f"Done. Updated {count} / {len(items)} items.")

    asyncio.run(_process_geo_updates())
