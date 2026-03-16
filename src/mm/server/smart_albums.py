"""Smart Albums — DB-backed album definitions with a generic filter system.

A "smart album" is a named set of ``query_media`` filters stored in the
``smart_albums`` table.  Two flavours exist:

* **Static albums** — fixed filters (e.g. "All Media", "Favorites").
* **Generator albums** — a single DB row whose ``generator`` field triggers
  automatic expansion into *N* child albums based on live data (tags,
  cameras, years, festivals, geo-clusters).

``build_smart_albums(repo)`` is the single entry-point consumed by the API.
It reads definitions from the DB, gathers the data needed by generators in
one parallel batch, expands generators, resolves a cover image for every
album, and returns structured section data ready for the frontend.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from lunar_python import Lunar

from uom.db.async_repository import AsyncRepository

# ═══════════════════════════════════════════════════════════
# Festival date helpers
# ═══════════════════════════════════════════════════════════


def _qingming_date(year: int) -> date:
    """Approximate Qingming solar date (April 4 or 5)."""
    day = 4 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 5
    return date(year, 4, day)


def _lunar_to_solar(year: int, month: int, day: int) -> date:
    s = Lunar.fromYmd(year, month, day).getSolar()
    return date(s.getYear(), s.getMonth(), s.getDay())


# ═══════════════════════════════════════════════════════════
# Location clustering
# ═══════════════════════════════════════════════════════════


def _cluster_locations(
    geo_items: list[dict[str, Any]],
    grid: float = 0.5,
    max_clusters: int = 50,
) -> list[dict[str, Any]]:
    """Grid-based location clustering.  Returns clusters with ≥2 items."""
    clusters: dict[str, dict[str, Any]] = {}
    for item in geo_items:
        lat, lon = item["lat"], item["lon"]
        clat = round(lat / grid) * grid
        clon = round(lon / grid) * grid
        key = f"{clat},{clon}"
        c = clusters.get(key)
        if c:
            c["count"] += 1
            if not c["city"] and item.get("city"):
                c["city"] = item["city"]
        else:
            clusters[key] = {
                "center_lat": clat,
                "center_lon": clon,
                "count": 1,
                "sample_id": item["id"],
                "city": item.get("city"),
            }
    result = [c for c in clusters.values() if c["count"] >= 2]
    result.sort(key=lambda c: c["count"], reverse=True)
    return result[:max_clusters]


# ═══════════════════════════════════════════════════════════
# Cover + count resolution
# ═══════════════════════════════════════════════════════════


def _filters_to_query_kwargs(filters: dict[str, Any]) -> dict[str, Any]:
    """Translate a smart-album filter dict to ``query_media()`` keyword args."""
    kw: dict[str, Any] = {}
    for k, v in filters.items():
        if v is None:
            continue
        if k == "type":
            kw["media_type"] = v
        elif k == "tag":
            kw["tag_names"] = [v]
        else:
            kw[k] = v
    return kw


async def _fetch_cover_and_count(
    repo: AsyncRepository, filters: dict[str, Any]
) -> tuple[int | None, int]:
    """Query the first matching media id **and** total count for *filters*."""
    items, total = await repo.query_media(page=1, per_page=1, **_filters_to_query_kwargs(filters))
    return (items[0].id if items else None), total


# ═══════════════════════════════════════════════════════════
# Generator expansion
# ═══════════════════════════════════════════════════════════


def _expand_per_tag(
    defn: dict[str, Any],
    tag_stats: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    albums: list[dict[str, Any]] = []
    for name, count in tag_stats:
        if count <= 0:
            continue
        albums.append(
            {
                "key": f"tag-{name}",
                "title": name,
                "count": count,
                "icon": defn["icon"],
                "color": defn["color"],
                "filters": {"tag": name, "sort": "date_taken", "order": "desc"},
                "search_text": name,
            }
        )
    return albums


def _expand_per_camera(
    defn: dict[str, Any],
    cameras: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    albums: list[dict[str, Any]] = []
    for cam in cameras:
        label = cam["model"] or cam["make"] or "Unknown"
        albums.append(
            {
                "key": f"cam-{cam['make']}-{cam['model']}",
                "title": label,
                "subtitle": cam["make"] if cam["make"] and cam["model"] else None,
                "count": cam["count"],
                "icon": defn["icon"],
                "filters": {"camera": label, "sort": "date_taken", "order": "desc"},
                "search_text": f"{cam['make']} {cam['model']} {label}",
            }
        )
    return albums


def _expand_per_year(
    defn: dict[str, Any],
    year_map: dict[str, int],
    unknown_date_count: int,
) -> list[dict[str, Any]]:
    albums: list[dict[str, Any]] = []
    for yr, count in sorted(year_map.items(), reverse=True):
        albums.append(
            {
                "key": f"yr-{yr}",
                "title": yr,
                "subtitle": f"{count:,} items",
                "count": count,
                "icon": defn["icon"],
                "filters": {
                    "date_from": f"{yr}-01-01",
                    "date_to": f"{yr}-12-31",
                    "sort": "date_taken",
                    "order": "desc",
                },
                "search_text": yr,
            }
        )
    if unknown_date_count > 0:
        albums.append(
            {
                "key": "yr-no-date",
                "title": "No Date",
                "subtitle": f"{unknown_date_count:,} items",
                "count": unknown_date_count,
                "icon": "help-circle",
                "filters": {"sort": "filename", "order": "asc", "no_date": True},
                "search_text": "no date unknown",
            }
        )
    return albums


def _expand_per_festival(
    defn: dict[str, Any],
    available_years: list[int],
    timeline_dates: set[str],
) -> list[dict[str, Any]]:
    config = defn.get("generator_config") or {}
    festivals = config.get("festivals", [])
    albums: list[dict[str, Any]] = []

    for f in festivals:
        # Collect date ranges across ALL years
        ranges: list[list[str]] = []
        for year in available_years:
            try:
                if f.get("solar_term"):
                    anchor = _qingming_date(year)
                else:
                    anchor = _lunar_to_solar(year, f["lunar_month"], f["lunar_day"])

                d_before = f.get("days_before", 0)
                d_after = f.get("days_after", 0)
                date_from = anchor - timedelta(days=d_before)
                date_to = anchor + timedelta(days=d_after)
                from_s = date_from.isoformat()
                to_s = date_to.isoformat()

                # Check if any timeline date falls in range
                has_photos = any(from_s <= d <= to_s for d in timeline_dates)
                if has_photos:
                    ranges.append([from_s, to_s])
            except Exception:
                continue

        if not ranges:
            continue

        albums.append(
            {
                "key": f["id"],
                "festival_id": f["id"],
                "title": f"{f.get('emoji', '🎉')} {f['name']}",
                "subtitle": None,  # will be set after count is resolved
                "icon": defn["icon"],
                "color": defn["color"],
                "filters": {
                    "date_ranges": ranges,
                    "sort": "date_taken",
                    "order": "desc",
                },
                "search_text": f"{f['name']} {f.get('search', '')}",
            }
        )

    return albums


def _expand_per_place(
    defn: dict[str, Any],
    geo_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    config = defn.get("generator_config") or {}
    grid = config.get("grid", 0.5)
    radius_km = config.get("radius_km", 30)
    max_clusters = config.get("max_clusters", 50)

    clusters = _cluster_locations(geo_data, grid=grid, max_clusters=max_clusters)
    albums: list[dict[str, Any]] = []
    for c in clusters:
        name = c["city"] or f"{c['center_lat']:.1f}°, {c['center_lon']:.1f}°"
        albums.append(
            {
                "key": f"loc-{c['center_lat']}-{c['center_lon']}",
                "title": name,
                "count": c["count"],
                "cover_id": c["sample_id"],  # pre-filled from geo data
                "icon": defn["icon"],
                "color": defn["color"],
                "filters": {
                    "lat": c["center_lat"],
                    "lon": c["center_lon"],
                    "radius": radius_km,
                },
                "search_text": name,
            }
        )
    return albums


# ═══════════════════════════════════════════════════════════
# Static album enrichment
# ═══════════════════════════════════════════════════════════


def _build_static_album(
    defn: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Convert a static DB definition into a response album dict.

    For well-known filter patterns the count is inferred from pre-fetched
    ``stats`` so we avoid extra queries.  Unknown patterns get ``count=None``
    and will be resolved during the batch cover pass.
    """
    filters: dict[str, Any] = defn.get("filters") or {}
    album: dict[str, Any] = {
        "key": defn["key"],
        "title": defn["title"],
        "subtitle": defn.get("subtitle") or None,
        "icon": defn["icon"],
        "color": defn.get("color") or None,
        "filters": filters,
        "search_text": defn["title"].lower(),
    }

    # ── Infer count from stats where possible ──
    active_keys = {k for k, v in filters.items() if k not in ("sort", "order") and v}
    if not active_keys:
        album["count"] = stats["total"]
    elif active_keys == {"type"}:
        album["count"] = stats["type_dist"].get(filters["type"], 0)
    elif active_keys == {"deleted"}:
        album["count"] = stats.get("trash_count", 0)
    # else: count will be resolved in cover batch

    if album.get("count") is not None and not album.get("subtitle"):
        album["subtitle"] = f"{album['count']:,} items"

    return album


# ═══════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════


async def build_smart_albums(repo: AsyncRepository) -> dict[str, Any]:
    """Build all smart album sections in one call.

    1. Load definitions from the ``smart_albums`` DB table.
    2. Gather base data (stats, timeline, tags, cameras, geo) in parallel.
    3. Expand generator definitions into child albums.
    4. Build static albums with inferred counts.
    5. Batch-resolve cover images for everything.
    6. Return ``{library: [...], tags: [...], ...}`` ready for the frontend.
    """

    # ── 1. Load definitions ──
    definitions = await repo.list_smart_album_definitions()

    # ── 2. Gather base data ──
    (
        stats_total,
        total_size,
        type_dist,
        cameras_raw,
        tag_stats_raw,
        timeline,
        geo_data,
    ) = await asyncio.gather(
        repo.get_total_media_count(),
        repo.total_size(),
        repo.type_distribution(),
        repo.cameras(),
        repo.tag_stats(),
        repo.timeline(),
        repo.geo_media(limit=5000),
    )

    # Process timeline → year_map + timeline_dates
    year_map: dict[str, int] = {}
    timeline_dates: set[str] = set()
    for entry in timeline:
        d = entry["date"]
        timeline_dates.add(d)
        yr = d[:4]
        year_map[yr] = year_map.get(yr, 0) + entry["count"]

    known_count = sum(year_map.values())
    unknown_date_count = max(0, stats_total - known_count)
    available_years = sorted([int(y) for y in year_map], reverse=True)
    tag_stats = [(n, c) for n, c in tag_stats_raw if c > 0]

    # Trash count (fast single query)
    _, trash_count = await repo.query_media(page=1, per_page=1, deleted=True)

    stats = {
        "total": stats_total,
        "total_size": total_size,
        "type_dist": type_dist,
        "trash_count": trash_count,
    }

    # ── 3. Process each definition ──
    sections: dict[str, list[dict[str, Any]]] = {}

    for defn in definitions:
        section = defn["section"]
        gen = defn.get("generator")

        if gen == "per_tag":
            expanded = _expand_per_tag(defn, tag_stats)
            sections.setdefault(section, []).extend(expanded)
        elif gen == "per_camera":
            expanded = _expand_per_camera(defn, cameras_raw)
            sections.setdefault(section, []).extend(expanded)
        elif gen == "per_year":
            expanded = _expand_per_year(defn, year_map, unknown_date_count)
            sections.setdefault(section, []).extend(expanded)
        elif gen == "per_festival":
            expanded = _expand_per_festival(defn, available_years, timeline_dates)
            sections.setdefault(section, []).extend(expanded)
        elif gen == "per_place":
            expanded = _expand_per_place(defn, geo_data)
            sections.setdefault(section, []).extend(expanded)
        elif gen:
            # Unknown generator — skip
            continue
        else:
            # Static album
            album = _build_static_album(defn, stats)
            # Skip empty static albums (count == 0) unless count unknown
            if album.get("count") == 0:
                continue
            sections.setdefault(section, []).append(album)

    # ── 4. Batch-resolve covers + counts ──
    needs_cover: list[tuple[str, dict[str, Any]]] = []
    for section_key, albums in sections.items():
        for album in albums:
            if "cover_id" not in album:
                needs_cover.append((section_key, album))

    if needs_cover:
        results = await asyncio.gather(
            *(_fetch_cover_and_count(repo, a["filters"]) for _, a in needs_cover)
        )
        for (section_key, album), (cover_id, total) in zip(needs_cover, results):
            album["cover_id"] = cover_id
            if album.get("count") is None:
                album["count"] = total
                if not album.get("subtitle"):
                    album["subtitle"] = f"{total:,} items"

    # Remove festivals with no cover (no photos at all)
    if "festivals" in sections:
        sections["festivals"] = [a for a in sections["festivals"] if a.get("cover_id") is not None]

    # ── 5. Ensure all expected section keys exist ──
    for key in ("library", "tags", "cameras", "festivals", "years", "places"):
        sections.setdefault(key, [])

    return sections
