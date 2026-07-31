"""Write organizer scrape outputs with one metadata policy."""

from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from mm.organizer.artwork import ArtworkPlan, download_artwork, plan_artworks
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.metadata_policy import external_track_nfo_candidate
from mm.organizer.nfo import NfoDocument, build_album_nfo, build_nfo, write_nfo
from mm.organizer.scraper_core import _normalize_score
from mm.organizer.scrapers import ScrapeCandidate


@dataclass(frozen=True)
class MetadataWriteResult:
    written: int
    targets: list[Path]


def metadata_detail(targets: list[Path]) -> str:
    if not targets:
        return "No missing metadata"
    names = [target.name for target in targets[:3]]
    suffix = f" +{len(targets) - 3}" if len(targets) > 3 else ""
    return ", ".join(names) + suffix


def write_standard_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> MetadataWriteResult:
    if candidate is None:
        return MetadataWriteResult(written=0, targets=[])
    document = build_nfo(item, candidate)
    targets = _metadata_targets_to_write(item, document, None, candidate, overwrite=overwrite)
    written = 1 if write_nfo_if_needed(document, overwrite=overwrite) else 0
    return MetadataWriteResult(written=written, targets=targets)


def write_album_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    if candidate is None:
        return 0
    return 1 if write_nfo_if_needed(build_album_nfo(item, candidate), overwrite=overwrite) else 0


def write_external_track_metadata(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    track_candidate = external_track_nfo_candidate(candidate)
    if not track_candidate:
        return 0
    return 1 if write_nfo_if_needed(build_nfo(item, track_candidate), overwrite=overwrite) else 0


def album_track_metadata_by_path(
    items: list[ParsedMediaFile],
    candidates: list[ScrapeCandidate],
) -> dict[Path, ScrapeCandidate]:
    if not items or not candidates:
        return {}
    item_by_path = {item.path: item for item in items}
    result: dict[Path, ScrapeCandidate] = {}
    used_candidates: set[int] = set()

    # Pass 1 (preferred): match on the song name parsed from the file
    # (bracket/feat/punctuation-insensitive). Robust when disc/track numbers
    # disagree with the online release.
    by_title: dict[str, list[int]] = {}
    for index, candidate in enumerate(candidates):
        key = _match_key(candidate.title)
        if key:
            by_title.setdefault(key, []).append(index)
    for item in _sorted_tracks(items):
        key = _match_key(item.title)
        pool = by_title.get(key) if key else None
        if not pool:
            continue
        candidate_index = next((i for i in pool if i not in used_candidates), None)
        if candidate_index is None:
            continue
        result[item.path] = candidates[candidate_index]
        used_candidates.add(candidate_index)

    # Confirm the album by name before trusting track numbers: if few tracks
    # matched by song name, the online tracklist is probably the wrong
    # album/edition (or a different disc split), so number/positional matching
    # would just force clearly-different names onto files. Leave the rest on
    # their filename-derived titles instead.
    denominator = min(len(items), len(candidates))
    if denominator == 0 or len(result) / denominator < _ALBUM_MATCH_RATIO:
        return _with_local_titles(result, item_by_path)

    # Pass 2: fall back to (disc, track) number, but only when the titles are
    # compatible. A wrong album/edition (or bonus/hidden tracks) must not force a
    # clearly-different song name onto a file just because the numbers line up.
    by_number: dict[tuple[int, int], tuple[int, ScrapeCandidate]] = {}
    for index, candidate in enumerate(candidates):
        if candidate.track is not None:
            by_number[(candidate.disc or 1, candidate.track)] = (index, candidate)
    for item in _sorted_tracks(items):
        if item.path in result or item.track is None:
            continue
        matched = by_number.get((item.disc or 1, item.track))
        if matched is None:
            continue
        candidate_index, candidate = matched
        if candidate_index in used_candidates:
            continue
        if not _titles_compatible(item.title, candidate.title):
            continue
        result[item.path] = candidate
        used_candidates.add(candidate_index)

    # Pass 3: positional fallback when the counts line up, with the same guard.
    remaining_items = [item for item in _sorted_tracks(items) if item.path not in result]
    remaining_candidates = [
        (index, candidate)
        for index, candidate in enumerate(candidates)
        if index not in used_candidates
    ]
    if remaining_items and len(remaining_items) == len(remaining_candidates):
        for item, (candidate_index, candidate) in zip(
            remaining_items, remaining_candidates, strict=True
        ):
            if _titles_compatible(item.title, candidate.title):
                result[item.path] = candidate
                used_candidates.add(candidate_index)
    return _with_local_titles(result, item_by_path)


_TRACK_TITLE_SIMILARITY = 0.6
# Fraction of tracks that must match by song name for the album/tracklist to be
# trusted enough to fall back to number/positional matching for the rest.
_ALBUM_MATCH_RATIO = 0.5


@lru_cache(maxsize=1)
def _t2s_converter():  # noqa: ANN202 - optional dependency type
    try:
        from opencc import OpenCC
    except ImportError:
        return None
    return OpenCC("t2s")


def _fold_script(text: str) -> str:
    # Fold traditional -> simplified so 龍的傳人 / 龙的传人 compare as equal.
    converter = _t2s_converter()
    return converter.convert(text) if converter else text


def _match_key(title: str | None) -> str:
    return _fold_script(_normalize_score(title or ""))


def _has_cjk(text: str) -> bool:
    return any(
        "\u3400" <= ch <= "\u9fff"  # CJK ideographs
        or "\u3040" <= ch <= "\u30ff"  # kana
        or "\uac00" <= ch <= "\ud7a3"  # hangul
        for ch in text
    )


def _prefer_local_title(item: ParsedMediaFile, candidate: ScrapeCandidate) -> ScrapeCandidate:
    """Source the track title from the local file, using the matched candidate
    only to enrich the rest (artist/album/year/track number/artwork/lyrics).

    The one exception is transliteration: a romanized/Latin filename paired with
    a CJK candidate keeps the proper CJK title (e.g. "Hei Se You Mo" -> "黑色幽默").
    """
    local_title = (item.title or "").strip()
    if not local_title:
        return candidate
    local_cjk = _has_cjk(_match_key(local_title))
    candidate_cjk = _has_cjk(_match_key(candidate.title))
    if candidate_cjk and not local_cjk:
        return candidate
    if local_title == (candidate.title or ""):
        return candidate
    title_variants = {
        language: local_title if value == candidate.title else value
        for language, value in candidate.title_variants.items()
    }
    title_variants["und"] = local_title
    return replace(
        candidate,
        title=local_title,
        title_variants=title_variants,
    )


def _with_local_titles(
    result: dict[Path, ScrapeCandidate],
    item_by_path: dict[Path, ParsedMediaFile],
) -> dict[Path, ScrapeCandidate]:
    return {
        path: _prefer_local_title(item_by_path[path], candidate)
        for path, candidate in result.items()
    }


def _titles_compatible(local_title: str | None, candidate_title: str | None) -> bool:
    local_key = _match_key(local_title)
    candidate_key = _match_key(candidate_title)
    if not local_key or not candidate_key or local_key == candidate_key:
        return True
    local_cjk = _has_cjk(local_key)
    candidate_cjk = _has_cjk(candidate_key)
    if local_cjk != candidate_cjk:
        # Allow a romanized/Latin filename to match CJK metadata (transliteration
        # of the same song), but never a CJK filename matching a Latin candidate:
        # a Chinese file paired with an English title means the online tracklist
        # is the wrong album/edition, not a transliteration.
        return candidate_cjk and not local_cjk
    return SequenceMatcher(None, local_key, candidate_key).ratio() >= _TRACK_TITLE_SIMILARITY


def write_track_lyrics(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> int:
    return 1 if _write_lyrics(item, candidate, overwrite) else 0


def artwork_plans(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> list[ArtworkPlan]:
    return plan_artworks(item, candidate, overwrite=overwrite)


def download_ready_artwork(plans: list[ArtworkPlan], *, timeout: float) -> int:
    count = 0
    for plan in plans:
        if plan.status != "ready":
            continue
        download_artwork(plan, timeout=timeout)
        count += 1
    return count


def write_nfo_if_needed(document: NfoDocument, *, overwrite: bool) -> bool:
    if document.target.exists() and not overwrite:
        return False
    write_nfo(document, overwrite=overwrite)
    return True


def _sorted_tracks(items: list[ParsedMediaFile]) -> list[ParsedMediaFile]:
    return sorted(
        items,
        key=lambda item: (
            item.disc or 1,
            item.track if item.track is not None else 9999,
            item.path.name.lower(),
        ),
    )


def _metadata_targets_to_write(
    item: ParsedMediaFile,
    document: NfoDocument,
    album_doc: NfoDocument | None,
    candidate: ScrapeCandidate | None,
    *,
    overwrite: bool,
) -> list[Path]:
    targets = [document.target]
    if album_doc is not None:
        targets.append(album_doc.target)
    lyric_target = _lyrics_target(item, candidate)
    if lyric_target is not None:
        targets.append(lyric_target)
    if overwrite:
        return targets
    return [target for target in targets if not target.exists()]


def _write_lyrics(
    item: ParsedMediaFile,
    candidate: ScrapeCandidate | None,
    overwrite: bool,
) -> bool:
    target = _lyrics_target(item, candidate)
    if target is None:
        return False
    text = candidate.synced_lyrics or candidate.lyrics if candidate else ""
    if not text.strip():
        return False
    if target.exists() and not overwrite:
        return False
    target.write_text(text, encoding="utf-8")
    return True


def _lyrics_target(item: ParsedMediaFile, candidate: ScrapeCandidate | None) -> Path | None:
    if item.media_type != "track" or not candidate:
        return None
    if candidate.synced_lyrics:
        return item.path.with_suffix(".lrc")
    if candidate.lyrics:
        return item.path.with_suffix(".lyrics.txt")
    return None
