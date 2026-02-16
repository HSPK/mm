from __future__ import annotations

import logging

import httpx

# In-memory cache for geocoding results
# Key: (lat: float, lon: float) -> str (city name)
_GEO_CACHE: dict[tuple[float, float], str] = {}

logger = logging.getLogger(__name__)


async def reverse_geocode(lat: float, lon: float) -> tuple[str | None, str | None, str | None]:
    """
    Reverse geocode a coordinate to a structured location: (label, country, city).
    Tries OpenStreetMap Nominatim first (10s timeout), then falls back to Photon (10s timeout).
    Uses httpx for async requests. Caches results in memory.
    """
    # Round to avoid cache misses on tiny differences
    lat_r = round(lat, 3)
    lon_r = round(lon, 3)
    key = (lat_r, lon_r)

    if key in _GEO_CACHE:
        # Cache stores the label for now, enhancing cache structure is future work or we just re-fetch
        # For simplicity in this refactor, if we want detailed fields, we might skip simple string cache
        # OR we change cache value to tuple. Let's assume we change cache to tuple.
        cached = _GEO_CACHE[key]
        if isinstance(cached, tuple):
            return cached
        # Old string cache hit? treat as label only
        return (cached, None, None)

    result = (None, None, None)  # label, country, city

    # 1. Try BigDataCloud first (User Request)
    try:
        result = await _reverse_geocode_bigdatacloud(lat, lon)
    except Exception as e:
        logger.error(f"BigDataCloud geocoding failed for {lat},{lon}: {e}")

    # 2. Try Nominatim (OSM) as fallback
    if not result[0]:
        try:
            result = await _reverse_geocode_nominatim(lat, lon)
        except Exception as e:
            logger.error(f"Nominatim geocoding failed for {lat},{lon}: {e}")

    # 3. Try Photon as second fallback
    if not result[0]:
        try:
            result = await _reverse_geocode_photon(lat, lon)
        except Exception as e:
            logger.error(f"Photon geocoding failed for {lat},{lon}: {e}")

    if result[0]:
        _GEO_CACHE[key] = result  # Cache the full tuple
        return result

    return (None, None, None)


async def _reverse_geocode_bigdatacloud(
    lat: float, lon: float
) -> tuple[str | None, str | None, str | None]:
    url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
    params = {
        "latitude": lat,
        "longitude": lon,
        "localityLanguage": "en",
    }
    # Mimic a browser to avoid "server-side operations" 402 error sometimes
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # BigDataCloud structure
        country = data.get("countryName")
        city = data.get("city") or data.get("locality")
        principal_subdivision = data.get("principalSubdivision")

        label = ""
        if city:
            label = city
            if principal_subdivision and principal_subdivision != city:
                label += f" · {principal_subdivision}"
        elif principal_subdivision:
            label = principal_subdivision

        return (label or None, country, city)


async def _reverse_geocode_nominatim(
    lat: float, lon: float
) -> tuple[str | None, str | None, str | None]:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,  # City level
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    headers = {"User-Agent": "uom-media-app/1.0"}

    # Short timeout (3.0s) because if blocked it usually hangs on connect
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        addr = data.get("address", {})

        country = addr.get("country")
        # Priority: specific city/district -> general
        city_name = addr.get("city") or addr.get("town") or addr.get("county")
        district = addr.get("district") or addr.get("suburb") or addr.get("neighbourhood")
        state = addr.get("state")

        label = ""
        if city_name:
            label = city_name
            if district and district != city_name:
                label += f" · {district}"
        elif state:
            label = state
            if district:
                label += f" · {district}"
        elif district:
            label = district
        else:
            display = data.get("display_name", "")
            label = display.split(",")[0] if display else None

        return (label, country, city_name)


async def _reverse_geocode_photon(
    lat: float, lon: float
) -> tuple[str | None, str | None, str | None]:
    url = "https://photon.komoot.io/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "lang": "en",  # Photon supports en, de, fr, it
    }
    # Photon requires User-Agent too
    headers = {"User-Agent": "uom-media-app/1.0"}

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            return (None, None, None)

        props = features[0].get("properties", {})

        country = props.get("country")
        city = props.get("city") or props.get("town") or props.get("village")
        state = props.get("state")
        name = props.get("name")

        label = ""
        if city:
            label = city
            if name and name != city:
                label += f" · {name}"
        elif state:
            label = state
            if city:
                label += f" · {city}"
            elif name:
                label += f" · {name}"
        elif name:
            label = name

        return (label or None, country, city)
