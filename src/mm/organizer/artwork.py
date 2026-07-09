"""Artwork download helpers."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import ScrapeCandidate


@dataclass(frozen=True)
class ArtworkPlan:
    source_url: str
    target: Path
    media_type: str
    status: str
    reason: str = ""


def plan_artwork(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool = False,
) -> ArtworkPlan:
    target = _artwork_target(item, "poster", candidate.poster_url if candidate else "")
    if not candidate or not candidate.poster_url:
        return ArtworkPlan("", target, item.media_type, "missing", "no artwork url")
    if target.exists() and not overwrite:
        return ArtworkPlan(candidate.poster_url, target, item.media_type, "exists", "target exists")
    return ArtworkPlan(candidate.poster_url, target, item.media_type, "ready")


def plan_artworks(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool = False,
) -> list[ArtworkPlan]:
    if not candidate:
        return [plan_artwork(item, candidate, overwrite=overwrite)]
    plans = [
        _plan_one(item, "poster", candidate.poster_url, overwrite=overwrite),
        _plan_one(item, "fanart", candidate.backdrop_url, overwrite=overwrite),
        _plan_one(item, "clearlogo", candidate.logo_url, overwrite=overwrite),
    ]
    return [plan for plan in plans if plan.source_url or plan.status == "missing"]


def _plan_one(
    item: ParsedMediaFile,
    kind: str,
    source_url: str,
    *,
    overwrite: bool,
) -> ArtworkPlan:
    target = _artwork_target(item, kind, source_url)
    if not source_url:
        return ArtworkPlan("", target, item.media_type, "missing", f"no {kind} url")
    if target.exists() and not overwrite:
        return ArtworkPlan(source_url, target, item.media_type, "exists", "target exists")
    return ArtworkPlan(source_url, target, item.media_type, "ready")


def download_artwork(plan: ArtworkPlan, *, timeout: float = 30.0) -> None:
    if plan.status != "ready":
        raise ValueError(f"Artwork plan is not ready: {plan.status}")
    plan.target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(plan.source_url, headers={"User-Agent": "litemm/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.URLError as err:
        raise RuntimeError(f"Could not download artwork: {err}") from err
    plan.target.write_bytes(data)


def _artwork_target(item: ParsedMediaFile, kind: str, source_url: str = "") -> Path:
    suffix = _url_suffix(source_url)
    if item.media_type == "tv":
        root = _tv_root(item.path)
        if kind == "poster" and item.season is not None:
            return root / f"season{item.season:02d}-poster{suffix}"
        return root / f"{kind}{suffix}"
    if item.media_type == "track":
        return item.path.parent / ("folder.jpg" if kind == "poster" else f"{kind}{suffix}")
    if item.media_type == "album":
        return item.path.parent / ("folder.jpg" if kind == "poster" else f"{kind}{suffix}")
    return item.path.parent / f"{kind}{suffix}"


def _tv_root(path: Path) -> Path:
    return path.parent.parent if path.parent.name.lower().startswith("season") else path.parent


def _url_suffix(source_url: str) -> str:
    suffix = Path(urllib.parse.urlparse(source_url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
