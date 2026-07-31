from __future__ import annotations

import asyncio
from copy import deepcopy

from mm.config import CliConfig, load_cli_config
from mm.db.client import AsyncDBClient
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.scrapers import (
    ScrapeCandidate,
    ScrapeQuery,
    album_signature_candidates,
)
from mm.server.organizer_matching import (
    _MIN_AUTO_CONFIDENCE,
    candidate_response,
    query_from_item,
    query_from_parsed,
)
from mm.server.organizer_schemas import OrganizerItem, OrganizerMatchResult
from mm.server.organizer_scrape_cache import (
    cached_album_track_candidates,
    cached_enrich_candidate,
    cached_search_all,
)

_MATCH_CONCURRENCY = 4


class OrganizerScrapeService:
    def __init__(
        self,
        db: AsyncDBClient,
        *,
        language: str | None = None,
        config: CliConfig | None = None,
    ) -> None:
        cfg = deepcopy(config or load_cli_config())
        if language:
            cfg.scrapers.language = language
        self.db = db
        self.config = cfg
        self.language = cfg.scrapers.language

    async def match_items(
        self,
        items: list[OrganizerItem],
        *,
        source: str | None,
        limit: int,
    ) -> list[OrganizerMatchResult]:
        semaphore = asyncio.Semaphore(_MATCH_CONCURRENCY)

        async def match(item: OrganizerItem) -> OrganizerMatchResult:
            async with semaphore:
                candidates = await self.search(
                    query_from_item(item),
                    source=source,
                    limit=limit,
                )
            return OrganizerMatchResult(
                item=item,
                candidates=[candidate_response(candidate) for candidate in candidates],
            )

        return list(await asyncio.gather(*(match(item) for item in items)))

    async def search(
        self,
        query: ScrapeQuery,
        *,
        source: str | None,
        limit: int = 5,
    ) -> list[ScrapeCandidate]:
        return await cached_search_all(
            self.db,
            query,
            source,
            limit=limit,
            cfg=self.config,
            language=self.language,
        )

    async def best_match(
        self,
        item: ParsedMediaFile,
        source: str | None,
    ) -> ScrapeCandidate | None:
        candidates = await self.search(query_from_parsed(item), source=source, limit=1)
        if not candidates:
            return None
        best = candidates[0]
        return best if best.confidence >= _MIN_AUTO_CONFIDENCE else None

    async def album_tracks(
        self,
        candidate: ScrapeCandidate | None,
        *,
        expected_count: int | None = None,
    ) -> list[ScrapeCandidate]:
        return await cached_album_track_candidates(
            self.db,
            candidate,
            expected_count=expected_count,
            cfg=self.config,
            language=self.language,
        )

    async def album_by_signature(
        self,
        query: ScrapeQuery,
        durations: list[float],
        *,
        source: str | None,
    ) -> tuple[ScrapeCandidate, list[ScrapeCandidate]] | None:
        return await asyncio.to_thread(
            album_signature_candidates,
            query,
            durations,
            cfg=self.config,
            source=source,
        )

    async def enrich(
        self,
        candidate: ScrapeCandidate | None,
        *,
        query: ScrapeQuery | None = None,
    ) -> ScrapeCandidate | None:
        return await cached_enrich_candidate(
            self.db,
            candidate,
            query=query,
            cfg=self.config,
            language=self.language,
        )
