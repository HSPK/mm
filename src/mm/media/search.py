"""Media search workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mm.db.sync_client import DBClient


@dataclass(frozen=True)
class MediaSearchItem:
    media_id: int
    path: str
    tags: str
    rank: int | None = None
    score: float | None = None


@dataclass(frozen=True)
class MediaSearchResult:
    kind: Literal["tags"]
    items: list[MediaSearchItem]
    tag_candidates: int | None = None


class MediaSearchError(RuntimeError):
    """Base class for expected media search failures."""


class NoSearchCriteria(MediaSearchError):
    pass


class NoTagMatches(MediaSearchError):
    pass


def search_media(
    db: DBClient,
    *,
    text_query: str | None = None,
    tag_names: list[str] | None = None,
    match_all_tags: bool = True,
    top_k: int = 10,
) -> MediaSearchResult:
    """Search media by tags."""
    tag_names = tag_names or []
    if text_query:
        raise NoSearchCriteria("Text search is unavailable until PostgreSQL vector search lands.")
    if not tag_names:
        raise NoSearchCriteria

    filter_ids = _tag_filter(db, tag_names, match_all_tags) if tag_names else None
    if tag_names and not filter_ids:
        raise NoTagMatches

    assert filter_ids is not None
    ids = sorted(filter_ids)[:top_k]
    return MediaSearchResult(
        kind="tags",
        tag_candidates=len(filter_ids),
        items=[item for media_id in ids if (item := _build_item(db, media_id)) is not None],
    )


def _tag_filter(db: DBClient, tag_names: list[str], match_all: bool) -> set[int]:
    return set(db.tag.media_ids(tag_names, match_all=match_all))


def _build_item(
    db: DBClient,
    media_id: int,
    *,
    rank: int | None = None,
    score: float | None = None,
) -> MediaSearchItem | None:
    media = db.media.get(media_id)
    if media is None:
        return None
    tags_info = db.tag.for_media(media_id)
    tag_str = ", ".join(tag.name for tag, _confidence in tags_info) if tags_info else ""
    return MediaSearchItem(
        media_id=media_id,
        path=media.path,
        tags=tag_str,
        rank=rank,
        score=score,
    )
