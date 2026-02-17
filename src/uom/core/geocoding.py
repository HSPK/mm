"""Offline reverse geocoding using GeoNames cities15000 dataset.

On first use, downloads ~2.5 MB from download.geonames.org and caches locally.
Subsequent calls use the cached data.  Query time: < 1 ms per coordinate.
Returns Chinese city/province names for CN/TW/HK/MO locations.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from typing import TypeAlias

    GeoResult: TypeAlias = tuple[str | None, str | None, str | None]

logger = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".cache" / "uom" / "geonames"

# ─── Country code → name ──────────────────────────────────

_CC_NAMES: dict[str, str] = {
    "CN": "China",
    "US": "United States",
    "JP": "Japan",
    "KR": "South Korea",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "AU": "Australia",
    "CA": "Canada",
    "TW": "Taiwan",
    "HK": "Hong Kong",
    "SG": "Singapore",
    "TH": "Thailand",
    "VN": "Vietnam",
    "MY": "Malaysia",
    "ID": "Indonesia",
    "PH": "Philippines",
    "IN": "India",
    "NZ": "New Zealand",
    "BR": "Brazil",
    "MX": "Mexico",
    "RU": "Russia",
    "NL": "Netherlands",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "CH": "Switzerland",
    "AT": "Austria",
    "PT": "Portugal",
    "IE": "Ireland",
    "CZ": "Czech Republic",
    "PL": "Poland",
    "TR": "Turkey",
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "EG": "Egypt",
    "ZA": "South Africa",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "GR": "Greece",
    "IL": "Israel",
    "IS": "Iceland",
    "HR": "Croatia",
    "HU": "Hungary",
    "RO": "Romania",
    "UA": "Ukraine",
    "KH": "Cambodia",
    "MM": "Myanmar",
    "LA": "Laos",
    "NP": "Nepal",
    "LK": "Sri Lanka",
    "BD": "Bangladesh",
    "PK": "Pakistan",
    "MN": "Mongolia",
    "KZ": "Kazakhstan",
    "MO": "Macao",
}

# ─── Chinese province names (admin1 English → 中文) ───────

_CN_ADMIN1_ZH: dict[str, str] = {
    "Anhui": "安徽",
    "Anhui Sheng": "安徽",
    "Beijing": "北京",
    "Chongqing": "重庆",
    "Chongqing Shi": "重庆",
    "Fujian": "福建",
    "Gansu": "甘肃",
    "Gansu Sheng": "甘肃",
    "Guangdong": "广东",
    "Guangxi": "广西",
    "Guangxi Zhuangzu Zizhiqu": "广西",
    "Guizhou": "贵州",
    "Guizhou Sheng": "贵州",
    "Hainan": "海南",
    "Hebei": "河北",
    "Heilongjiang": "黑龙江",
    "Heilongjiang Sheng": "黑龙江",
    "Henan": "河南",
    "Henan Sheng": "河南",
    "Hubei": "湖北",
    "Hunan": "湖南",
    "Inner Mongolia": "内蒙古",
    "Jiangsu": "江苏",
    "Jiangsu Sheng": "江苏",
    "Jiangxi": "江西",
    "Jiangxi Sheng": "江西",
    "Jilin": "吉林",
    "Jilin Sheng": "吉林",
    "Liaoning": "辽宁",
    "Ningxia": "宁夏",
    "Ningxia Huizu Zizhiqu": "宁夏",
    "Qinghai": "青海",
    "Qinghai Sheng": "青海",
    "Shaanxi": "陕西",
    "Shandong": "山东",
    "Shandong Sheng": "山东",
    "Shanghai": "上海",
    "Shanghai Shi": "上海",
    "Shanxi": "山西",
    "Shanxi Sheng": "山西",
    "Sichuan": "四川",
    "Tianjin": "天津",
    "Tianjin Shi": "天津",
    "Tibet": "西藏",
    "Tibet Autonomous Region": "西藏",
    "Xinjiang": "新疆",
    "Xinjiang Uygur Zizhiqu": "新疆",
    "Yunnan": "云南",
    "Zhejiang": "浙江",
    "Zhejiang Sheng": "浙江",
}

_TW_ADMIN1_ZH: dict[str, str] = {
    "Taiwan": "台湾",
    "Taipei": "台北",
    "Kaohsiung": "高雄",
    "Taichung": "台中",
    "Tainan": "台南",
}


# ─── CJK helpers ──────────────────────────────────────────


def _has_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def _is_pure_cjk(text: str) -> bool:
    """Check if text contains ONLY CJK ideographs (no kana, latin, etc.)."""
    return all("\u4e00" <= c <= "\u9fff" for c in text)


def _is_simplified(text: str) -> bool:
    """Check if text is simplified Chinese (encodable as GB2312)."""
    try:
        text.encode("gb2312")
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


_ADMIN_SUFFIXES = frozenset("市区省县镇乡旗盟")


def _best_zh_name(alt_names: str) -> str | None:
    """Pick the best simplified Chinese name from comma-separated alternate names.

    Key heuristic: if ``name + '市'`` also exists in the alternates list,
    that name is the official city name (深圳→深圳市 ✓, 宝安→宝安市 ✗ → 深圳 wins).
    """
    all_names = {n.strip() for n in alt_names.split(",") if n.strip()}
    candidates: list[tuple[str, int]] = []
    for i, name in enumerate(alt_names.split(",")):
        name = name.strip()
        if name and 2 <= len(name) <= 6 and _is_pure_cjk(name):
            candidates.append((name, i))
    if not candidates:
        return None

    def _score(item: tuple[str, int]) -> tuple:
        name, pos = item
        simplified = _is_simplified(name)
        has_suffix = name[-1] in _ADMIN_SUFFIXES
        # Official city name: name+市 exists in alternates
        has_shi_form = (name + "市") in all_names
        # Prefer: has 市-form (official), simplified, no suffix, shorter, earlier
        return (not has_shi_form, not simplified, has_suffix, len(name), pos)

    best = min(candidates, key=_score)
    result = best[0]
    # Strip trailing 市 suffix (e.g. 上海市 → 上海)
    if len(result) > 2 and result[-1] == "市":
        result = result[:-1]
    return result


# ─── Data download & loading ──────────────────────────────


def _ensure_data() -> None:
    """Download GeoNames data files if not cached."""
    import urllib.request

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cities_file = _CACHE_DIR / "cities15000.txt"
    admin1_file = _CACHE_DIR / "admin1CodesASCII.txt"

    if not cities_file.exists():
        logger.info("Downloading GeoNames cities15000 (~2.5 MB)...")
        url = "https://download.geonames.org/export/dump/cities15000.zip"
        zip_path = _CACHE_DIR / "cities15000.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract("cities15000.txt", _CACHE_DIR)
        zip_path.unlink()
        logger.info("GeoNames cities15000 downloaded.")

    if not admin1_file.exists():
        logger.info("Downloading GeoNames admin1 codes...")
        url = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
        urllib.request.urlretrieve(url, admin1_file)
        logger.info("GeoNames admin1 codes downloaded.")


# ─── City geocoder (numpy brute-force, no scipy needed) ───


class _CityGeocoder:
    """Nearest-city geocoder using GeoNames cities15000 + numpy."""

    def __init__(self) -> None:
        _ensure_data()

        # Load admin1 codes:  "CN.01" → "Anhui Sheng"
        admin1_map: dict[str, str] = {}
        admin1_file = _CACHE_DIR / "admin1CodesASCII.txt"
        with open(admin1_file, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    admin1_map[parts[0]] = parts[1]

        # Parse cities15000.txt (GeoNames TSV, no header)
        # Columns: 0=id 1=name 2=ascii 3=alternates 4=lat 5=lon
        #          8=cc 10=admin1_code 14=population
        cities: list[dict] = []
        cities_file = _CACHE_DIR / "cities15000.txt"
        with open(cities_file, encoding="utf-8") as f:
            for line in f:
                parts = line.split("\t")
                if len(parts) < 15:
                    continue
                cc = parts[8]
                admin1_code = f"{cc}.{parts[10]}"
                admin1_en = admin1_map.get(admin1_code, "")

                # For CJK regions, extract Chinese name
                zh_name = None
                if cc in ("CN", "TW", "HK", "MO"):
                    zh_name = _best_zh_name(parts[3])

                # Resolve admin1 to Chinese for CN/TW
                admin1_zh = None
                if cc == "CN":
                    admin1_zh = _CN_ADMIN1_ZH.get(admin1_en)
                elif cc == "TW":
                    admin1_zh = _TW_ADMIN1_ZH.get(admin1_en)

                cities.append(
                    {
                        "name": parts[1],
                        "zh_name": zh_name,
                        "lat": float(parts[4]),
                        "lon": float(parts[5]),
                        "cc": cc,
                        "admin1": admin1_en,
                        "admin1_zh": admin1_zh,
                        "population": int(parts[14]) if parts[14] else 0,
                    }
                )

        self.cities = cities

        # Build ECEF coordinates for nearest-neighbor search
        lats = np.radians(np.array([c["lat"] for c in cities], dtype=np.float32))
        lons = np.radians(np.array([c["lon"] for c in cities], dtype=np.float32))
        self._coords = np.column_stack(
            [
                np.cos(lats) * np.cos(lons),
                np.cos(lats) * np.sin(lons),
                np.sin(lats),
            ]
        )  # shape: (N, 3)

        # Population array for scoring
        self._populations = np.array([max(c["population"], 1000) for c in cities], dtype=np.float32)
        # Pre-compute population weight: pop^0.6 (larger cities "attract" from farther)
        self._pop_weight = np.power(self._populations, 0.6)

        logger.info(f"Geocoder loaded: {len(cities)} cities")

    def _to_ecef(self, coords: list[tuple[float, float]]) -> np.ndarray:
        """Convert (lat, lon) pairs to ECEF unit vectors."""
        arr = np.array(coords, dtype=np.float32)
        lats = np.radians(arr[:, 0])
        lons = np.radians(arr[:, 1])
        return np.column_stack(
            [
                np.cos(lats) * np.cos(lons),
                np.cos(lats) * np.sin(lons),
                np.sin(lats),
            ]
        )

    def query(self, coords: list[tuple[float, float]]) -> list[GeoResult]:
        """Find nearest city for each (lat, lon) coordinate.

        Uses population-weighted distance: nearby big cities beat tiny
        neighborhoods that happen to be marginally closer.
        """
        if not coords:
            return []

        query_ecef = self._to_ecef(coords)  # (Q, 3)
        K = 32  # candidates per query
        n_cities = len(self.cities)
        k = min(K, n_cities)

        chunk_size = 200
        indices = np.empty(len(coords), dtype=np.intp)

        for i in range(0, len(coords), chunk_size):
            chunk = query_ecef[i : i + chunk_size]  # (C, 3)
            # Squared Euclidean distance in ECEF space
            diffs = chunk[:, np.newaxis, :] - self._coords[np.newaxis, :, :]  # (C, N, 3)
            dists = np.sum(diffs * diffs, axis=2)  # (C, N)

            # Find top-K nearest candidates per query
            top_k_idx = np.argpartition(dists, k, axis=1)[:, :k]  # (C, K)

            # Score: distance / pop_weight — lower is better
            # Gather distances and pop weights for candidates
            c_range = np.arange(chunk.shape[0])[:, np.newaxis]
            top_k_dists = dists[c_range, top_k_idx]  # (C, K)
            top_k_pop_w = self._pop_weight[top_k_idx]  # (C, K)
            scores = top_k_dists / top_k_pop_w  # (C, K)

            best_in_k = np.argmin(scores, axis=1)  # (C,)
            indices[i : i + chunk.shape[0]] = top_k_idx[np.arange(chunk.shape[0]), best_in_k]

        # Format results
        results: list[GeoResult] = []
        for idx in indices:
            city = self.cities[idx]
            cc = city["cc"]
            country = _CC_NAMES.get(cc, cc)

            # City name: prefer Chinese for CJK regions
            city_name = city["zh_name"] or city["name"]

            # Admin1 (province/state): prefer Chinese for CN/TW
            admin1 = city["admin1_zh"] or city["admin1"]

            # Build label: "City · Province"
            # Skip province if it's same as city (e.g. 北京 · 北京 → 北京)
            label = city_name
            if admin1 and admin1 != city_name and admin1 != city["name"]:
                label += f" · {admin1}"

            results.append((label, country, city_name))

        return results


# ─── Singleton ─────────────────────────────────────────────

_geocoder: _CityGeocoder | None = None


def _get_geocoder() -> _CityGeocoder:
    global _geocoder
    if _geocoder is None:
        _geocoder = _CityGeocoder()
    return _geocoder


# ─── Public API ────────────────────────────────────────────


async def reverse_geocode(lat: float, lon: float) -> GeoResult:
    """
    Reverse geocode a coordinate to (label, country, city).
    Offline — uses GeoNames cities15000 dataset cached locally.
    """
    return _get_geocoder().query([(lat, lon)])[0]


def reverse_geocode_sync(lat: float, lon: float) -> GeoResult:
    """Synchronous reverse geocode."""
    return _get_geocoder().query([(lat, lon)])[0]


def reverse_geocode_batch(
    coords: list[tuple[float, float]],
) -> list[GeoResult]:
    """
    Batch reverse geocode.
    Processes all coordinates at once — significantly faster than one-by-one.
    """
    return _get_geocoder().query(coords)
