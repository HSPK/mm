from __future__ import annotations

import json
from pathlib import Path

import mm.server.organizer_sync_jobs as sync
from mm.config import CliConfig
from mm.db.models import JobModel, OrganizerMediaModel
from mm.db.sync_client import DBClient
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_scan import iter_media_files
from mm.server.organizer_schemas import OrganizerItem
from mm.server.organizer_sources import OrganizerSourceResolver


def test_iter_media_files_skips_apple_double(tmp_path: Path):
    album = tmp_path / "Album"
    album.mkdir()
    (album / "01. Song.mp3").write_bytes(b"x")
    (album / "._01. Song.mp3").write_bytes(b"x")  # AppleDouble sidecar
    (album / ".DS_Store").write_bytes(b"x")

    names = {file.name for file in iter_media_files(album, recursive=True)}
    assert names == {"01. Song.mp3"}


def test_sync_job_scans_and_persists_in_parallel(db: DBClient, tmp_path: Path):
    album = tmp_path / "王力宏" / "Синглы" / "2011 - 火力全開"
    album.mkdir(parents=True)
    (album / "01.火力全開.mp3").write_bytes(b"x")
    (album / "02.需要人陪.mp3").write_bytes(b"x")
    (album / "._01.火力全開.mp3").write_bytes(b"x")  # AppleDouble twin must be ignored
    direct = tmp_path / "王力宏" / "1999 - 不可能錯過你"
    direct.mkdir(parents=True)
    (direct / "07.不降落的滑翔翼.mp3").write_bytes(b"x")

    payload = json.dumps({"paths": [str(tmp_path)], "recursive": True})
    job_id = "test-sync-parallel"
    db._run(
        db._client.objects.create(
            JobModel, id=job_id, kind="sync", payload=payload, status="queued"
        )
    )

    db._run(sync.run_sync_job(db._client, job_id))

    job = db._run(db._client.objects.get(JobModel, id=job_id))
    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))

    assert job.status == "done"
    assert job.progress == 100
    assert len(rows) == 3
    assert all(row.artist == "王力宏" for row in rows)


def test_sync_job_handles_empty_source(db: DBClient, tmp_path: Path):
    payload = json.dumps({"paths": [str(tmp_path)], "recursive": True})
    job_id = "test-sync-empty"
    db._run(
        db._client.objects.create(
            JobModel, id=job_id, kind="sync", payload=payload, status="queued"
        )
    )

    db._run(sync.run_sync_job(db._client, job_id))

    job = db._run(db._client.objects.get(JobModel, id=job_id))
    assert job.status == "done"


def test_sync_only_reparses_changed_media_and_sidecars(db: DBClient, tmp_path: Path, monkeypatch):
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    first = album / "01. First.mp3"
    second = album / "02. Second.mp3"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    cfg = CliConfig()
    cfg.organizer.media_sources = {"movies": [], "tv": [], "music": [str(tmp_path)]}
    monkeypatch.setattr(sync, "load_cli_config", lambda: cfg)

    def run(job_id: str) -> dict[str, int]:
        db._run(
            db._client.objects.create(
                JobModel,
                id=job_id,
                kind="sync",
                payload=json.dumps({"paths": [str(tmp_path)], "recursive": True}),
                status="queued",
            )
        )
        db._run(sync.run_sync_job(db._client, job_id))
        job = db._run(db._client.objects.get(JobModel, id=job_id))
        assert job.status == "done"
        return json.loads(job.result)

    assert run("incremental-first") == {"items": 2, "updated": 2, "unchanged": 0}
    first_revisions = {
        row.path: row.revision
        for row in db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    }

    original = sync._parse_and_build
    parsed: list[Path] = []

    def counted_parse(path, context):
        parsed.append(path)
        return original(path, context)

    monkeypatch.setattr(sync, "_parse_and_build", counted_parse)
    assert run("incremental-noop") == {"items": 2, "updated": 0, "unchanged": 2}
    assert parsed == []
    assert {
        row.path: row.revision
        for row in db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    } == first_revisions

    first.write_bytes(b"first changed")
    assert run("incremental-media-change") == {"items": 2, "updated": 1, "unchanged": 1}
    assert parsed == [first]

    parsed.clear()
    (album / "album.nfo").write_text("<album><title>Changed Album</title></album>")
    assert run("incremental-sidecar-change") == {"items": 2, "updated": 2, "unchanged": 0}
    assert set(parsed) == {first, second}


def test_persist_scan_items_return_modes(db: DBClient):
    item = OrganizerItem(path="/lib/a.mp3", media_type="track", title="零缺点", artist="孙燕姿")

    first = db._run(persist_scan_items(db._client, [item]))
    assert len(first) == 1
    assert first[0].is_new is True  # first time seen
    assert first[0].title == "零缺点"  # model_copy keeps the original values

    again = db._run(persist_scan_items(db._client, [item]))
    assert again[0].is_new is False  # already persisted

    skipped = db._run(persist_scan_items(db._client, [item], return_items=False))
    assert skipped == []  # result-building skipped for count-only callers
    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    assert len(rows) == 1  # still upserted despite not returning items


def test_persist_resolves_each_item_once_with_one_config_load(db: DBClient, monkeypatch):
    cfg = CliConfig()
    cfg.organizer.media_sources = {
        "movies": ["/library/movies"],
        "tv": [],
        "music": [],
    }
    config_loads = 0

    def load_config():
        nonlocal config_loads
        config_loads += 1
        return cfg

    resolutions = 0
    original = OrganizerSourceResolver.resolve_item

    def resolve_item(resolver, item):
        nonlocal resolutions
        resolutions += 1
        return original(resolver, item)

    monkeypatch.setattr("mm.server.organizer_sources.load_cli_config", load_config)
    monkeypatch.setattr(OrganizerSourceResolver, "resolve_item", resolve_item)
    items = [
        OrganizerItem(
            path=f"/library/movies/Movie {index}.mkv",
            media_type="movie",
            title=f"Movie {index}",
        )
        for index in range(50)
    ]

    db._run(persist_scan_items(db._client, items, return_items=False))

    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    assert config_loads == 1
    assert resolutions == len(items)
    assert {row.source_root for row in rows} == {"/library/movies"}


def test_source_resolver_prefers_the_most_specific_configured_root(tmp_path: Path):
    cfg = CliConfig()
    cfg.organizer.media_sources = {
        "movies": [str(tmp_path)],
        "tv": [str(tmp_path / "Shows")],
        "music": [],
    }
    resolver = OrganizerSourceResolver.from_config(cfg)
    item = OrganizerItem(
        path=str(tmp_path / "Shows" / "Example" / "episode.mkv"),
        media_type="movie",
        title="Example",
    )

    source = resolver.resolve_item(item)

    assert source.kind == "tv"
    assert source.root == (tmp_path / "Shows").resolve()


def test_source_resolver_preserves_fallback_for_ambiguous_roots(tmp_path: Path):
    cfg = CliConfig()
    cfg.organizer.media_sources = {
        "movies": [str(tmp_path)],
        "tv": [str(tmp_path)],
        "music": [],
    }
    resolver = OrganizerSourceResolver.from_config(cfg)
    item = OrganizerItem(
        path=str(tmp_path / "Album" / "track.flac"),
        media_type="track",
        title="Track",
    )

    source = resolver.resolve_item(item)

    assert source.kind == "music"
    assert source.root == tmp_path.resolve()
