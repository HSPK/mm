from __future__ import annotations

from mm.config import CliConfig
from mm.organizer import scrapers
from mm.organizer.scrapers import (
    ScrapeCandidate,
    ScrapeQuery,
    build_scrapers,
    configured_source_rows,
)


def test_scraper_config_defaults_have_tmdb_source():
    cfg = CliConfig()

    rows = configured_source_rows(cfg)
    assert rows[0][0] == "tmdb"
    assert rows[0][1] == "yes"
    assert rows[0][2] == "yes"
    assert rows[0][3] == "no"
    assert any(row[0] == "musicbrainz" and row[2] == "yes" for row in rows)
    assert any(row[0] == "itunes" and row[2] == "yes" for row in rows)
    assert any(row[0] == "netease" and row[2] == "yes" for row in rows)
    assert any(row[0] == "qqmusic" and row[2] == "yes" for row in rows)


def test_build_scrapers_skips_disabled_sources():
    cfg = CliConfig()
    cfg.scrapers.sources["tmdb"].enabled = False

    assert build_scrapers(cfg, only="tmdb") == []


def test_build_scrapers_includes_music_sources():
    names = [scraper.name for scraper in build_scrapers(CliConfig())]

    assert "musicbrainz" in names
    assert "itunes" in names
    assert "netease" in names
    assert "qqmusic" in names


def test_enrich_track_candidate_uses_external_title_for_lyrics(monkeypatch):
    calls: list[tuple[str, str, str, str]] = []

    def fake_lyrics(source: str, track: str, artist: str, album: str):
        calls.append((source, track, artist, album))
        return {"plainLyrics": "lyrics", "syncedLyrics": ""}

    monkeypatch.setattr(scrapers, "_lyrics_from_source", fake_lyrics)
    candidate = ScrapeCandidate(
        source="qqmusic",
        source_id="1",
        media_type="track",
        title="以父之名",
        artist="周杰伦",
        album="叶惠美",
    )
    query = ScrapeQuery(
        media_type="track",
        title="In the name of the father",
        artist="Jay Chou",
        album="Ye Hui Mei",
    )

    enriched = scrapers.enrich_candidate(candidate, query=query, cfg=CliConfig())

    assert enriched is not None
    assert enriched.lyrics == "lyrics"
    assert calls == [("lrclib", "以父之名", "周杰伦", "叶惠美")]
