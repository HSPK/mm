"""Persistent cache for scrape searches and album tracklists.

Repeat scrapes (re-runs, overlapping albums, re-scans) reuse prior results
instead of re-hitting the network, keyed by the normalized query so equivalent
queries share an entry. Mirrors the video_probe_cache approach.
"""

from __future__ import annotations

import asyncio
import dataclasses
import datetime as dt
import hashlib
import json
import threading
from collections.abc import Awaitable, Callable
from weakref import WeakKeyDictionary

from peewee import EXCLUDED

from mm.config import CliConfig
from mm.db.client import AsyncDBClient
from mm.db.models import ScrapeCacheModel
from mm.organizer.scraper_core import normalize_for_match
from mm.organizer.scrapers import (
    ScrapeCandidate,
    ScrapeQuery,
    album_track_candidates,
    enrich_candidate,
    search_all,
)

_TTL = dt.timedelta(days=30)
_EMPTY_TTL = dt.timedelta(hours=1)
_CACHE_VERSION = "v8"
_CACHE_LOCKS: WeakKeyDictionary[
    asyncio.AbstractEventLoop,
    dict[tuple[str, str], asyncio.Lock],
] = WeakKeyDictionary()
_CACHE_LOCKS_GUARD = threading.Lock()


def _cache_key(*parts: str) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _config_fingerprint(cfg: CliConfig | None) -> str:
    if cfg is None:
        return ""
    data = {
        "language": cfg.scrapers.language,
        "order": cfg.scrapers.order,
        "lyrics_source": cfg.organizer.lyrics_source,
        "sources": {
            name: source.model_dump(mode="json")
            for name, source in sorted(cfg.scrapers.sources.items())
        },
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _query_parts(query: ScrapeQuery) -> list[str]:
    return [
        query.media_type,
        normalize_for_match(query.title or ""),
        normalize_for_match(query.artist or ""),
        normalize_for_match(query.album or ""),
        str(query.year or ""),
        str(query.season or ""),
        str(query.episode or ""),
        str(query.track or ""),
    ]


def _search_key(
    query: ScrapeQuery,
    source: str | None,
    limit: int,
    language: str,
    config_fingerprint: str = "",
) -> str:
    return _cache_key(
        _CACHE_VERSION,
        "search",
        source or "",
        language,
        config_fingerprint,
        str(limit),
        *_query_parts(query),
    )


def _serialize(candidates: list[ScrapeCandidate]) -> str:
    return json.dumps(
        [dataclasses.asdict(candidate) for candidate in candidates], ensure_ascii=False
    )


def _deserialize(payload: str) -> list[ScrapeCandidate]:
    try:
        rows = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return [ScrapeCandidate(**row) for row in rows if isinstance(row, dict)]


async def _get_fresh(db: AsyncDBClient, key: str) -> list[ScrapeCandidate] | None:
    try:
        row = await db.objects.get(ScrapeCacheModel, cache_key=key)
    except ScrapeCacheModel.DoesNotExist:
        return None
    candidates = _deserialize(row.payload)
    ttl = _TTL if candidates else _EMPTY_TTL
    if row.created_at and dt.datetime.now() - row.created_at > ttl:
        await db.objects.execute(ScrapeCacheModel.delete().where(ScrapeCacheModel.cache_key == key))
        return None
    return candidates


async def _store(db: AsyncDBClient, key: str, candidates: list[ScrapeCandidate]) -> None:
    payload = _serialize(candidates)
    now = dt.datetime.now()
    await db.objects.execute(
        ScrapeCacheModel.insert(
            cache_key=key,
            payload=payload,
            created_at=now,
        ).on_conflict(
            conflict_target=[ScrapeCacheModel.cache_key],
            update={
                ScrapeCacheModel.payload: EXCLUDED.payload,
                ScrapeCacheModel.created_at: EXCLUDED.created_at,
            },
        )
    )


async def cached_search_all(
    db: AsyncDBClient,
    query: ScrapeQuery,
    source: str | None,
    *,
    limit: int = 5,
    cfg: CliConfig | None = None,
    language: str = "",
) -> list[ScrapeCandidate]:
    effective_language = language or (cfg.scrapers.language if cfg else "")
    key = _search_key(
        query,
        source,
        limit,
        effective_language,
        _config_fingerprint(cfg),
    )

    async def load() -> list[ScrapeCandidate]:
        kwargs: dict[str, object] = {"source": source, "limit": limit}
        if cfg is not None:
            kwargs["cfg"] = cfg
        return await asyncio.to_thread(
            search_all,
            query,
            **kwargs,
        )

    return await _cached_candidates(db, key, load)


async def cached_album_track_candidates(
    db: AsyncDBClient,
    candidate: ScrapeCandidate | None,
    *,
    expected_count: int | None = None,
    cfg: CliConfig | None = None,
    language: str = "",
) -> list[ScrapeCandidate]:
    if candidate is None:
        return []
    key = _cache_key(
        _CACHE_VERSION,
        "tracks",
        candidate.source,
        candidate.source_id,
        language,
        _config_fingerprint(cfg),
        str(expected_count or ""),
    )

    async def load() -> list[ScrapeCandidate]:
        kwargs: dict[str, object] = {"expected_count": expected_count}
        if cfg is not None:
            kwargs["cfg"] = cfg
        return await asyncio.to_thread(
            album_track_candidates,
            candidate,
            **kwargs,
        )

    return await _cached_candidates(db, key, load)


async def cached_enrich_candidate(
    db: AsyncDBClient,
    candidate: ScrapeCandidate | None,
    *,
    query: ScrapeQuery | None = None,
    cfg: CliConfig | None = None,
    language: str = "",
) -> ScrapeCandidate | None:
    if candidate is None:
        return None
    key = _cache_key(
        _CACHE_VERSION,
        "details",
        candidate.source,
        candidate.source_id,
        language,
        _config_fingerprint(cfg),
        *(_query_parts(query) if query else []),
    )

    async def load() -> list[ScrapeCandidate]:
        enriched = await asyncio.to_thread(
            enrich_candidate,
            candidate,
            query=query,
            cfg=cfg,
        )
        return [enriched] if enriched and enriched != candidate else []

    candidates = await _cached_candidates(db, key, load)
    return candidates[0] if candidates else candidate


async def _cached_candidates(
    db: AsyncDBClient,
    key: str,
    load: Callable[[], Awaitable[list[ScrapeCandidate]]],
) -> list[ScrapeCandidate]:
    cached = await _get_fresh(db, key)
    if cached is not None:
        return cached
    lock = _cache_lock(db, key)
    async with lock:
        cached = await _get_fresh(db, key)
        if cached is not None:
            return cached
        candidates = await load()
        await _store(db, key, candidates)
        return candidates


def _cache_lock(db: AsyncDBClient, key: str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock_key = (str(db.database), key)
    with _CACHE_LOCKS_GUARD:
        loop_locks = _CACHE_LOCKS.setdefault(loop, {})
        lock = loop_locks.setdefault(lock_key, asyncio.Lock())
        if len(loop_locks) > 1024:
            for existing_key, existing_lock in tuple(loop_locks.items()):
                if existing_key != lock_key and not existing_lock.locked():
                    loop_locks.pop(existing_key, None)
                if len(loop_locks) <= 1024:
                    break
    return lock
