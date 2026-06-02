"""Location-label update workflow for media metadata."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from mm.db.sync_client import DBClient
from mm.geo.geocoding import reverse_geocode_batch

GeoResult = tuple[str | None, str | None, str | None]


@dataclass(frozen=True)
class LocationUpdateRow:
    metadata_id: int | None
    gps: str
    location: str
    country: str | None
    city: str | None
    updated: bool


@dataclass(frozen=True)
class LocationUpdateResult:
    candidates: int
    valid: int
    updated: int
    elapsed: float
    rows: list[LocationUpdateRow]


def update_location_labels(
    db: DBClient,
    *,
    reparse: bool = False,
    geocode: Callable[[list[tuple[float, float]]], list[GeoResult]] = reverse_geocode_batch,
    on_progress: Callable[[LocationUpdateRow], None] | None = None,
) -> LocationUpdateResult:
    """Resolve GPS metadata to location labels and persist them."""
    items = db.metadata.needing_geo(force_reparse=reparse)
    valid = [(md, md.gps_lat, md.gps_lon) for md in items if md.gps_lat and md.gps_lon]
    if not valid:
        return LocationUpdateResult(
            candidates=len(items),
            valid=0,
            updated=0,
            elapsed=0.0,
            rows=[],
        )

    coords = [(lat, lon) for _, lat, lon in valid]
    started = time.perf_counter()
    results = geocode(coords)
    elapsed = time.perf_counter() - started

    updated = 0
    rows: list[LocationUpdateRow] = []
    for (metadata, lat, lon), (label, country, city) in zip(valid, results):
        gps = f"{lat:.4f},{lon:.4f}"
        if not label:
            row = LocationUpdateRow(metadata.id, gps, "No result", "-", "-", False)
            rows.append(row)
            if on_progress:
                on_progress(row)
            continue

        try:
            db.metadata.update_location(metadata.id, label, country=country, city=city)
        except Exception as exc:
            row = LocationUpdateRow(metadata.id, gps, f"Error: {exc}", "-", "-", False)
        else:
            row = LocationUpdateRow(metadata.id, gps, label, country, city, True)
            updated += 1
        rows.append(row)
        if on_progress:
            on_progress(row)

    return LocationUpdateResult(
        candidates=len(items),
        valid=len(valid),
        updated=updated,
        elapsed=elapsed,
        rows=rows,
    )
