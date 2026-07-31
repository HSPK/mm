from __future__ import annotations

import asyncio
import time
import urllib.error
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import mm.organizer.music_platform_scrapers as platform_scrapers
import mm.organizer.scraper_core as sc
import mm.server.organizer_scrape_cache as cache
import mm.server.organizer_scrape_jobs as scrape_jobs
from mm.config import CliConfig
from mm.db.sync_client import DBClient
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.localization import localized_variants, select_localized_name
from mm.organizer.musicbrainz_scraper import MusicBrainzScraper
from mm.organizer.scrapers import ScrapeCandidate, ScrapeQuery
from mm.server.organizer_matching import (
    candidate_from_body,
    candidate_response,
    parsed_from_item,
)
from mm.server.organizer_schemas import OrganizerCandidate, OrganizerItem
from mm.server.organizer_scrape_service import OrganizerScrapeService


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._body


def test_http_client_retries_on_503_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "busy", {}, None)
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(sc.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(sc.time, "sleep", lambda *_: None)

    client = sc.HttpJsonClient(timeout=1, max_retries=2, backoff=0)
    assert client.get("http://example.com/api", {}) == {"ok": True}
    assert calls["n"] == 2


def test_http_client_does_not_retry_on_404(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)

    monkeypatch.setattr(sc.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(sc.time, "sleep", lambda *_: None)

    client = sc.HttpJsonClient(timeout=1)
    with pytest.raises(sc.ScraperError):
        client.get("http://example.com/api", {})
    assert calls["n"] == 1


def test_musicbrainz_gets_one_per_second_interval():
    assert sc._host_min_interval("musicbrainz.org") >= 1.0
    assert sc._host_min_interval("itunes.apple.com") < 1.0


def test_music_confidence_normalizes_brackets_and_feat():
    query = ScrapeQuery(media_type="track", title="Song", artist="A", album="Album")
    score = sc.music_confidence(query, title="Song (Live) feat. B", artist="A", album="Album")
    assert score > 0.9


def test_music_confidence_keeps_cjk():
    # Bracket qualifier is stripped and CJK is preserved, so the title matches
    # exactly; 0.88 is the max without an album (title 0.64 + artist 0.24).
    query = ScrapeQuery(media_type="track", title="我不难过", artist="孙燕姿", album="")
    assert sc.music_confidence(query, title="我不难过 [Live]", artist="孙燕姿", album="") >= 0.88


def test_candidate_mapper_roundtrip_and_field_parity():
    assert {f.name for f in fields(ScrapeCandidate)} == set(OrganizerCandidate.model_fields)
    candidate = ScrapeCandidate(
        source="mb",
        source_id="1",
        media_type="track",
        title="X",
        artist="A",
        genres=["pop"],
        confidence=0.8,
    )
    assert candidate_from_body(candidate_response(candidate)) == candidate


def test_musicbrainz_details_select_chinese_aliases():
    source = CliConfig().scrapers.sources["musicbrainz"]
    scraper = MusicBrainzScraper(source, timeout=1, language="zh-CN")

    def get(url, params, headers=None):
        if "/artist/" in url:
            return {
                "name": "Jay Chou",
                "aliases": [
                    {"name": "周杰伦", "locale": "zh-CN", "primary": True},
                    {"name": "周杰倫", "locale": "zh-TW", "primary": True},
                ],
            }
        return {
            "title": "Fantasy",
            "aliases": [
                {"name": "范特西", "locale": "zh-CN", "primary": True},
            ],
            "artist-credit": [
                {
                    "name": "Jay Chou",
                    "artist": {"id": "artist-mbid", "name": "Jay Chou"},
                }
            ],
        }

    scraper.client.get = get
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="release-group-mbid",
        media_type="album",
        title="Fantasy",
        artist="Jay Chou",
        external_ids={"musicbrainz_artist": "artist-mbid"},
    )

    localized = scraper.details(candidate)

    assert localized.source_id == candidate.source_id
    assert localized.title == "范特西"
    assert localized.artist == "周杰伦"
    assert localized.original_title == "Fantasy"
    assert localized.title_variants["zh-cn"] == "范特西"
    assert localized.artist_variants["zh-tw"] == "周杰倫"


def test_musicbrainz_details_preserve_all_localized_artist_credits():
    source = CliConfig().scrapers.sources["musicbrainz"]
    scraper = MusicBrainzScraper(source, timeout=1, language="zh-CN")

    def get(url, params, headers=None):
        if "/artist/first" in url:
            return {
                "name": "First",
                "aliases": [{"name": "甲", "locale": "zh-CN", "primary": True}],
            }
        if "/artist/second" in url:
            return {
                "name": "Second",
                "aliases": [{"name": "乙", "locale": "zh-CN", "primary": True}],
            }
        return {
            "title": "Duet",
            "artist-credit": [
                {"name": "First", "artist": {"id": "first", "name": "First"}},
                {"name": "Second", "artist": {"id": "second", "name": "Second"}},
            ],
        }

    scraper.client.get = get
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="recording",
        media_type="track",
        title="Duet",
    )

    localized = scraper.details(candidate)

    assert localized.artist == "甲, 乙"
    assert localized.artist_variants["und"] == "First, Second"
    assert localized.external_ids["musicbrainz_artist_credit"] == "first+second"


def test_chinese_platform_multi_artist_credit_ids_include_every_artist():
    first = {"artists": [{"id": 1}, {"id": 2}]}
    second = {"artists": [{"id": 1}, {"id": 3}]}

    assert platform_scrapers._netease_artist_credit_ids(first) != (
        platform_scrapers._netease_artist_credit_ids(second)
    )


def test_netease_album_signature_localizes_translated_album_and_tracks():
    source = CliConfig().scrapers.sources["netease"]
    scraper = platform_scrapers.NeteaseScraper(source, timeout=1)

    def request(url, *, data=None, params=None):
        if data and data.get("type") == "100":
            return {
                "result": {
                    "artists": [
                        {
                            "id": 7763,
                            "name": "G.E.M.邓紫棋",
                            "alias": ["G.E.M."],
                        }
                    ]
                }
            }
        if "/artist/albums/" in url:
            return {
                "hotAlbums": [
                    {
                        "id": 74989312,
                        "name": "睡皇后",
                        "size": 3,
                        "publishTime": 1544716800000,
                    }
                ],
                "more": False,
            }
        return {
            "album": {
                "id": 74989312,
                "name": "睡皇后",
                "publishTime": 1544716800000,
                "artist": {"id": 7763, "name": "G.E.M.邓紫棋"},
            },
            "songs": [
                {
                    "id": 1,
                    "name": "岩石里的花",
                    "dt": 294120,
                    "no": 1,
                    "ar": [{"id": 7763, "name": "G.E.M.邓紫棋"}],
                },
                {
                    "id": 2,
                    "name": "WHY",
                    "dt": 221280,
                    "no": 2,
                    "ar": [{"id": 7763, "name": "G.E.M.邓紫棋"}],
                },
                {
                    "id": 3,
                    "name": "睡皇后",
                    "dt": 236466,
                    "no": 3,
                    "ar": [{"id": 7763, "name": "G.E.M.邓紫棋"}],
                },
            ],
        }

    scraper._request_json = request
    result = scraper.album_by_signature(
        ScrapeQuery(
            media_type="album",
            title="Sleeping Queen EP",
            artist="邓紫棋",
            year=2018,
        ),
        [294.1649, 221.3094, 236.5127],
    )

    assert result is not None
    album, tracks = result
    assert album.title == "睡皇后"
    assert album.artist == "邓紫棋"
    assert [track.title for track in tracks] == ["岩石里的花", "WHY", "睡皇后"]
    assert all(track.album == "睡皇后" for track in tracks)


def test_netease_album_signature_rejects_different_recording_durations():
    source = CliConfig().scrapers.sources["netease"]
    scraper = platform_scrapers.NeteaseScraper(source, timeout=1)
    scraper._artist_id = lambda _artist: "7763"
    scraper._artist_albums = lambda _artist_id: [
        {
            "id": 74989312,
            "name": "睡皇后",
            "size": 3,
            "publishTime": 1544716800000,
        }
    ]
    scraper._request_json = lambda _url: {
        "album": {
            "id": 74989312,
            "name": "睡皇后",
            "publishTime": 1544716800000,
        },
        "songs": [
            {"id": 1, "name": "Wrong 1", "dt": 100000},
            {"id": 2, "name": "Wrong 2", "dt": 110000},
            {"id": 3, "name": "Wrong 3", "dt": 120000},
        ],
    }

    assert (
        scraper.album_by_signature(
            ScrapeQuery(
                media_type="album",
                title="Sleeping Queen EP",
                artist="邓紫棋",
                year=2018,
            ),
            [294.1649, 221.3094, 236.5127],
        )
        is None
    )


def test_validated_album_candidate_uses_duration_signature_for_translated_titles(
    tmp_path: Path,
):
    album = ParsedMediaFile(
        path=tmp_path / "Sleeping Queen EP",
        media_type="album",
        title="Sleeping Queen EP",
        artist="邓紫棋",
        album_artist="邓紫棋",
        album="Sleeping Queen EP",
        year=2018,
    )
    tracks = [
        ParsedMediaFile(
            path=tmp_path / f"{index:02d}.mp3",
            media_type="track",
            title=title,
            artist="邓紫棋",
            album_artist="邓紫棋",
            album="Sleeping Queen EP",
            year=2018,
            track=index,
            duration=duration,
        )
        for index, (title, duration) in enumerate(
            [
                ("Flower in the Rock", 294.1649),
                ("Why", 221.3094),
                ("Sleeping Queen", 236.5127),
            ],
            start=1,
        )
    ]
    candidate = ScrapeCandidate(
        source="netease",
        source_id="74989312",
        media_type="album",
        title="睡皇后",
        artist="邓紫棋",
        album_artist="邓紫棋",
        album="睡皇后",
    )
    external_tracks = [
        replace(
            candidate,
            source_id=str(index),
            media_type="track",
            title=title,
            track=index,
        )
        for index, title in enumerate(["岩石里的花", "WHY", "睡皇后"], start=1)
    ]

    class Service:
        async def search(self, *args, **kwargs):
            return []

        async def album_by_signature(self, query, durations, *, source):
            assert durations == [294.1649, 221.3094, 236.5127]
            return candidate, external_tracks

    matched_album, matched_tracks = asyncio.run(
        scrape_jobs._validated_album_candidate(
            Service(),
            album,
            tracks,
            "netease",
        )
    )

    assert matched_album is not None and matched_album.title == "睡皇后"
    assert [matched_tracks[track.path].title for track in tracks] == [
        "岩石里的花",
        "WHY",
        "睡皇后",
    ]
    assert matched_album.title_variants["und"] == "Sleeping Queen EP"
    assert matched_tracks[tracks[0].path].title_variants["und"] == "Flower in the Rock"


def test_parsed_from_item_preserves_audio_probe_fields():
    parsed = parsed_from_item(
        OrganizerItem(
            path="/music/song.flac",
            media_type="track",
            title="Song",
            duration=123.5,
            mime_type="audio/flac",
        )
    )

    assert parsed.duration == 123.5
    assert parsed.mime_type == "audio/flac"


def test_localized_name_falls_back_between_chinese_scripts():
    assert (
        select_localized_name(
            {"zh-TW": "周杰倫"},
            "zh-CN",
            "Jay Chou",
        )
        == "周杰伦"
    )


def test_locale_less_alias_does_not_replace_canonical_name():
    assert (
        localized_variants(
            "Canonical",
            [{"name": "Unscoped Alias", "locale": None}],
        )["und"]
        == "Canonical"
    )


def test_scrape_cache_serves_second_call_from_db(db: DBClient, monkeypatch):
    calls = {"n": 0}

    def fake_search(query, *, source=None, limit=5):
        calls["n"] += 1
        return [
            ScrapeCandidate(
                source="mb", source_id="1", media_type="album", title="X", confidence=0.9
            )
        ]

    monkeypatch.setattr(cache, "search_all", fake_search)
    query = ScrapeQuery(media_type="album", title="X", artist="A")

    first = db._run(cache.cached_search_all(db._client, query, None, limit=1))
    second = db._run(cache.cached_search_all(db._client, query, None, limit=1))

    assert first == second
    assert len(first) == 1 and first[0].title == "X"
    assert calls["n"] == 1  # second call served from the persistent cache


def test_scrape_cache_keys_use_structured_encoding():
    assert cache._cache_key("A|B", "C") != cache._cache_key("A", "B|C")


def test_scrape_cache_separates_languages_and_full_query(db: DBClient, monkeypatch):
    calls: list[tuple[str, int | None]] = []

    def fake_search(query, *, cfg=None, source=None, limit=5):
        calls.append((cfg.scrapers.language, query.season))
        return [
            ScrapeCandidate(
                source=source or "tmdb",
                source_id=f"{cfg.scrapers.language}-{query.season}",
                media_type="tv",
                title=query.title,
                confidence=0.9,
            )
        ]

    monkeypatch.setattr(cache, "search_all", fake_search)
    zh_cfg = CliConfig()
    zh_cfg.scrapers.language = "zh-CN"
    en_cfg = CliConfig()
    en_cfg.scrapers.language = "en-US"
    season_one = ScrapeQuery(media_type="tv", title="Show", season=1)
    season_two = ScrapeQuery(media_type="tv", title="Show", season=2)

    db._run(
        cache.cached_search_all(
            db._client,
            season_one,
            "tmdb",
            limit=1,
            cfg=zh_cfg,
            language="zh-CN",
        )
    )
    db._run(
        cache.cached_search_all(
            db._client,
            season_one,
            "tmdb",
            limit=1,
            cfg=en_cfg,
            language="en-US",
        )
    )
    db._run(
        cache.cached_search_all(
            db._client,
            season_two,
            "tmdb",
            limit=1,
            cfg=zh_cfg,
            language="zh-CN",
        )
    )
    db._run(
        cache.cached_search_all(
            db._client,
            season_one,
            "tmdb",
            limit=1,
            cfg=zh_cfg,
            language="zh-CN",
        )
    )

    assert calls == [("zh-CN", 1), ("en-US", 1), ("zh-CN", 2)]


def test_scrape_cache_coalesces_same_key_requests(db: DBClient, monkeypatch):
    calls = {"n": 0}

    def fake_search(query, *, cfg=None, source=None, limit=5):
        calls["n"] += 1
        time.sleep(0.05)
        return [
            ScrapeCandidate(
                source="tmdb",
                source_id="same",
                media_type=query.media_type,
                title=query.title,
                confidence=0.9,
            )
        ]

    monkeypatch.setattr(cache, "search_all", fake_search)
    cfg = CliConfig()
    query = ScrapeQuery(media_type="movie", title="Movie")

    async def search_twice():
        return await asyncio.gather(
            cache.cached_search_all(
                db._client,
                query,
                "tmdb",
                cfg=cfg,
                language="zh-CN",
            ),
            cache.cached_search_all(
                db._client,
                query,
                "tmdb",
                cfg=cfg,
                language="zh-CN",
            ),
        )

    first, second = db._run(search_twice())

    assert first == second
    assert calls["n"] == 1


def test_scrape_service_applies_requested_language(db: DBClient, monkeypatch):
    languages = []

    def fake_search(query, *, cfg=None, source=None, limit=5):
        languages.append(cfg.scrapers.language)
        return [
            ScrapeCandidate(
                source="tmdb",
                source_id="movie",
                media_type="movie",
                title="映画",
                confidence=0.9,
            )
        ]

    monkeypatch.setattr(cache, "search_all", fake_search)
    service = OrganizerScrapeService(db._client, language="ja-JP")
    results = db._run(
        service.match_items(
            [OrganizerItem(path="/media/movie.mkv", media_type="movie", title="Movie")],
            source="tmdb",
            limit=1,
        )
    )

    assert service.language == "ja-JP"
    assert results[0].candidates[0].title == "映画"
    assert languages == ["ja-JP"]


def test_scrape_service_caches_enriched_details_per_language(db: DBClient, monkeypatch):
    languages = []

    def fake_enrich(candidate, *, query=None, cfg=None):
        languages.append(cfg.scrapers.language)
        return replace(candidate, overview=cfg.scrapers.language)

    monkeypatch.setattr(cache, "enrich_candidate", fake_enrich)
    candidate = ScrapeCandidate(
        source="tmdb",
        source_id="42",
        media_type="movie",
        title="Movie",
    )
    query = ScrapeQuery(media_type="movie", title="Movie")
    zh_service = OrganizerScrapeService(db._client, language="zh-CN")
    en_service = OrganizerScrapeService(db._client, language="en-US")

    first = db._run(zh_service.enrich(candidate, query=query))
    second = db._run(zh_service.enrich(candidate, query=query))
    english = db._run(en_service.enrich(candidate, query=query))

    assert first == second
    assert first is not None and first.overview == "zh-CN"
    assert english is not None and english.overview == "en-US"
    assert languages == ["zh-CN", "en-US"]


def test_missing_enrichment_uses_short_cache_ttl(db: DBClient, monkeypatch):
    calls = {"n": 0}

    def unchanged(candidate, *, query=None, cfg=None):
        calls["n"] += 1
        return candidate

    monkeypatch.setattr(cache, "enrich_candidate", unchanged)
    candidate = ScrapeCandidate(
        source="tmdb",
        source_id="missing-details",
        media_type="movie",
        title="Movie",
    )
    service = OrganizerScrapeService(db._client, language="en-US")

    db._run(service.enrich(candidate))
    from mm.db.models import ScrapeCacheModel

    db._run(
        db._client.objects.execute(
            ScrapeCacheModel.update(
                created_at=cache.dt.datetime.now() - cache.dt.timedelta(hours=2)
            )
        )
    )
    db._run(service.enrich(candidate))

    assert calls["n"] == 2


def test_enrichment_cache_tracks_result_affecting_config(db: DBClient, monkeypatch):
    sources = []

    def fake_enrich(candidate, *, query=None, cfg=None):
        sources.append(cfg.organizer.lyrics_source)
        return replace(candidate, lyrics=cfg.organizer.lyrics_source)

    monkeypatch.setattr(cache, "enrich_candidate", fake_enrich)
    candidate = ScrapeCandidate(
        source="musicbrainz",
        source_id="track",
        media_type="track",
        title="Track",
    )
    first_cfg = CliConfig()
    first_cfg.organizer.lyrics_source = "lrclib"
    second_cfg = CliConfig()
    second_cfg.organizer.lyrics_source = "netease"

    first = db._run(OrganizerScrapeService(db._client, config=first_cfg).enrich(candidate))
    second = db._run(OrganizerScrapeService(db._client, config=second_cfg).enrich(candidate))

    assert first is not None and first.lyrics == "lrclib"
    assert second is not None and second.lyrics == "netease"
    assert sources == ["lrclib", "netease"]


def test_artwork_batch_waits_for_all_downloads_before_reporting_failure(db: DBClient, monkeypatch):
    completed = []

    def download(plans, *, timeout):
        plan = plans[0]
        if plan.name == "fail":
            raise OSError("failed")
        time.sleep(0.05)
        completed.append(plan.name)

    monkeypatch.setattr(scrape_jobs, "download_ready_artwork", download)
    plans = [
        SimpleNamespace(status="ready", name="fail"),
        SimpleNamespace(status="ready", name="slow"),
    ]

    with pytest.raises(scrape_jobs.ArtworkBatchError) as error:
        db._run(scrape_jobs._download_ready_artwork(plans, timeout=1))

    assert completed == ["slow"]
    assert error.value.completed == 1


class _FakeScraper:
    def __init__(self, name, results=None, error=None):
        self.name = name
        self._results = results or []
        self._error = error

    def search(self, query, *, limit=5):
        if self._error is not None:
            raise self._error
        return self._results[:limit]


def _candidate(source, title, confidence):
    return ScrapeCandidate(
        source=source, source_id="1", media_type="track", title=title, confidence=confidence
    )


def test_search_all_merges_and_sorts_sources(monkeypatch):
    import mm.organizer.scrapers as scrapers

    scraper_a = _FakeScraper("a", [_candidate("a", "Low", 0.4)])
    scraper_b = _FakeScraper("b", [_candidate("b", "High", 0.9)])
    monkeypatch.setattr(
        scrapers,
        "build_scrapers",
        lambda cfg=None, *, only=None: [
            scraper_a,
            scraper_b,
        ],
    )

    results = scrapers.search_all(ScrapeQuery(media_type="track", title="x"), limit=5)

    assert [c.title for c in results] == ["High", "Low"]  # sorted by confidence desc


def test_search_all_isolates_a_failing_source(monkeypatch):
    import mm.organizer.scrapers as scrapers

    good = _FakeScraper("good", [_candidate("good", "Keep", 0.8)])
    bad = _FakeScraper("bad", error=RuntimeError("boom"))
    monkeypatch.setattr(scrapers, "build_scrapers", lambda cfg=None, *, only=None: [good, bad])

    results = scrapers.search_all(ScrapeQuery(media_type="track", title="x"), limit=5)

    assert [c.title for c in results] == ["Keep"]  # one source down, the other still used


def test_search_all_raises_when_every_source_fails(monkeypatch):
    import mm.organizer.scrapers as scrapers

    bad1 = _FakeScraper("bad1", error=RuntimeError("boom1"))
    bad2 = _FakeScraper("bad2", error=RuntimeError("boom2"))
    monkeypatch.setattr(scrapers, "build_scrapers", lambda cfg=None, *, only=None: [bad1, bad2])

    with pytest.raises(RuntimeError):
        scrapers.search_all(ScrapeQuery(media_type="track", title="x"), limit=5)


def test_qq_lyrics_configuration_uses_fast_fallback_order(monkeypatch):
    import mm.organizer.scrapers as scrapers

    calls = []

    def lyrics(source, track, artist, album):
        calls.append(source)
        return {"plainLyrics": "lyrics"} if source == "netease" else None

    cfg = CliConfig()
    cfg.organizer.lyrics_source = "qq"
    monkeypatch.setattr(scrapers, "_lyrics_from_source", lyrics)
    candidate = ScrapeCandidate(
        source="local",
        source_id="",
        media_type="track",
        title="Song",
    )

    enriched = scrapers.enrich_candidate(candidate, cfg=cfg)

    assert enriched.lyrics == "lyrics"
    assert calls == ["lrclib", "netease"]
