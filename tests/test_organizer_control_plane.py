from __future__ import annotations

import asyncio
import datetime as dt
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from mm.config import CliConfig
from mm.db.models import JobModel, OrganizerMediaModel
from mm.db.sync_client import DBClient
from mm.organizer.artwork import (
    _atomic_write_no_follow,
    _download_artwork_bytes,
    _safe_artwork_url,
    extract_embedded_artwork,
)
from mm.organizer.scrapers import ScrapeCandidate
from mm.server.job_system import job_service
from mm.server.job_utils import update_job
from mm.server.organizer_capabilities import capabilities_response
from mm.server.organizer_matching import selected_candidate
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_schemas import (
    OrganizerCandidate,
    OrganizerItem,
    OrganizerItemPatchRequest,
    OrganizerItemsPatchBody,
    OrganizerRevealDirectoryBody,
)
from mm.server.organizer_scrape_cache import _store
from mm.server.routers.organizer import (
    items as list_items,
)
from mm.server.routers.organizer import (
    patch_items,
    reveal_item_directory,
)


def test_artwork_rejects_local_ssrf_targets():
    with pytest.raises(ValueError, match="not allowed"):
        _safe_artwork_url("http://localhost/poster.jpg")


def test_artwork_revalidates_redirect_targets(monkeypatch):
    class Response:
        status = 302

        @staticmethod
        def getheader(name):
            return "http://127.0.0.1/private.jpg" if name == "Location" else None

        @staticmethod
        def read(*_):
            return b""

    class Connection:
        def request(self, *_args, **_kwargs):
            pass

        @staticmethod
        def getresponse():
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(
        "mm.organizer.artwork.socket.getaddrinfo",
        lambda host, *_args, **_kwargs: [
            (
                None,
                None,
                None,
                None,
                (
                    "93.184.216.34" if host == "example.com" else "127.0.0.1",
                    80,
                ),
            )
        ],
    )
    monkeypatch.setattr("mm.organizer.artwork._pinned_connection", lambda *_args: Connection())
    with pytest.raises(ValueError, match="non-public"):
        _download_artwork_bytes("http://example.com/poster.jpg", timeout=1)


def test_artwork_atomic_install_replaces_symlink_without_following_it(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"original")
    target = tmp_path / "poster.jpg"
    target.symlink_to(outside)

    _atomic_write_no_follow(target, b"image")

    assert outside.read_bytes() == b"original"
    assert not target.is_symlink()
    assert target.read_bytes() == b"image"


def test_embedded_album_artwork_is_extracted_to_album_root(tmp_path, monkeypatch):
    image = BytesIO()
    Image.new("RGB", (2, 2), "red").save(image, format="JPEG")
    monkeypatch.setattr(
        "mutagen.File",
        lambda _path: SimpleNamespace(tags={"cover": SimpleNamespace(data=image.getvalue())}),
    )
    album = tmp_path / "Album"
    album.mkdir()

    target = extract_embedded_artwork([album / "track.mp3"], album)

    assert target == album / "cover.jpg"
    assert target.is_file()


def test_ad_hoc_or_partial_scan_does_not_hide_sibling_items(db: DBClient, monkeypatch, tmp_path):
    root = tmp_path / "music"
    first = OrganizerItem(path=str(root / "one.mp3"), media_type="track", title="One")
    second = OrganizerItem(path=str(root / "two.mp3"), media_type="track", title="Two")
    cfg = CliConfig()
    cfg.organizer.media_sources = {"movies": [], "tv": [], "music": [str(root)]}
    monkeypatch.setattr("mm.server.organizer_sources.load_cli_config", lambda: cfg)

    db._run(persist_scan_items(db._client, [first, second]))
    # /scan's default is discovery only: seeing one item does not hide its sibling.
    db._run(persist_scan_items(db._client, [first]))
    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    assert {row.path for row in rows if not row.missing} == {first.path, second.path}

    # A full root commit is intentionally scoped to that root.
    db._run(
        persist_scan_items(
            db._client,
            [first],
            mark_missing=True,
            completed_roots=[root],
        )
    )
    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    assert next(row for row in rows if row.path == first.path).missing == 0
    assert next(row for row in rows if row.path == second.path).missing == 1


def test_organizer_items_returns_the_complete_database_projection(db: DBClient, tmp_path):
    episodes = [
        OrganizerItem(
            path=str(tmp_path / "Example Show" / "Season 01" / f"episode-{index:03d}.mkv"),
            media_type="tv",
            title="Example Show",
            season=1,
            episode=index,
        )
        for index in range(1, 206)
    ]
    db._run(persist_scan_items(db._client, episodes, return_items=False))

    response = db._run(list_items(kind="tv", _u=None, db=db._client))

    assert len(response.items) == 205
    assert {item.path for item in response.items} == {item.path for item in episodes}


def test_reveal_album_directory_uses_internal_item_ids(db: DBClient, tmp_path, monkeypatch):
    album = tmp_path / "Artist" / "Album"
    tracks = []
    for disc, name in ((1, "one.flac"), (2, "two.flac")):
        path = album / f"CD{disc}" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        tracks.append(
            OrganizerItem(
                path=str(path),
                media_type="track",
                title=name,
                artist="Artist",
                album="Album",
                disc=disc,
            )
        )
    db._run(persist_scan_items(db._client, tracks, return_items=False))
    rows = db._run(
        db._client.objects.fetchall(
            OrganizerMediaModel.select(OrganizerMediaModel.item_uid).where(
                OrganizerMediaModel.path.in_([item.path for item in tracks])
            )
        )
    )
    monkeypatch.setattr(
        "mm.server.organizer_paths.configured_media_roots",
        lambda: [tmp_path],
    )
    opened = []
    monkeypatch.setattr(
        "mm.server.routers.organizer.open_in_file_manager",
        lambda path: opened.append(path) or True,
    )
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    response = db._run(
        reveal_item_directory(
            OrganizerRevealDirectoryBody(item_uids=[row.item_uid for row in rows]),
            request,
            _u=None,
            db=db._client,
        )
    )

    assert response == {"revealed": True}
    assert opened == [album]


def test_cancel_cas_prevents_late_done_from_overwriting_cancel(db: DBClient):
    now = dt.datetime.now()
    db._run(
        db._client.objects.create(
            JobModel,
            id="cancel-cas",
            kind="sync",
            status="running",
            created_at=now,
            updated_at=now,
        )
    )
    db._run(job_service.cancel(db._client, "cancel-cas"))
    assert db._run(update_job(db._client, "cancel-cas", status="done", progress=100)) is False
    db._run(update_job(db._client, "cancel-cas", status="canceled", progress=100))
    assert db._run(db._client.objects.get(JobModel, id="cancel-cas")).status == "canceled"


def test_canceling_job_converges_to_canceled_after_runner_exit(db: DBClient):
    now = dt.datetime.now()
    db._run(
        db._client.objects.create(
            JobModel,
            id="cancel-finalize",
            kind="sync",
            status="canceling",
            created_at=now,
            updated_at=now,
        )
    )

    db._run(job_service.run(db._client, "cancel-finalize"))

    assert db._run(db._client.objects.get(JobModel, id="cancel-finalize")).status == "canceled"


def test_job_idempotency_claim_is_atomic(db: DBClient, monkeypatch):
    monkeypatch.setattr(job_service, "enqueue", lambda *_args, **_kwargs: None)

    async def create_twice():
        return await asyncio.gather(
            *[
                job_service.create(
                    db._client,
                    kind="sync",
                    title="Sync",
                    payload='{"paths":[],"recursive":true}',
                    idempotency_key="same-request",
                )
                for _ in range(2)
            ]
        )

    first, second = db._run(create_twice())

    assert first.id == second.id
    assert db._run(db._client.objects.count(JobModel.select())) == 1


def test_capabilities_are_registry_backed():
    result = capabilities_response()
    assert {"movie", "tv", "track"} <= {item["media_type"] for item in result["media_types"]}
    assert "musicbrainz" in result["scraper_adapters"]


def test_selected_scrape_candidate_uses_internal_item_uid():
    item = OrganizerItem(
        path="/media/movie.mkv",
        item_uid="movie-uid",
        media_type="movie",
        title="Movie",
    )
    candidate = OrganizerCandidate(
        source="tmdb",
        source_id="123",
        media_type="movie",
        title="Selected Movie",
    )
    body = SimpleNamespace(
        source="tmdb",
        selected_candidates={"movie-uid": candidate},
    )

    selected = selected_candidate(body, item)

    assert selected is not None
    assert selected.source_id == "123"


def test_scrape_cache_concurrent_store_is_an_upsert(db: DBClient):
    async def store_twice():
        await asyncio.gather(
            _store(
                db._client,
                "same-key",
                [ScrapeCandidate("one", "1", "movie", "One")],
            ),
            _store(
                db._client,
                "same-key",
                [ScrapeCandidate("two", "2", "movie", "Two")],
            ),
        )

    db._run(store_twice())

    from mm.db.models import ScrapeCacheModel

    assert db._run(db._client.objects.count(ScrapeCacheModel.select())) == 1


def test_batch_patch_revision_conflict_rolls_back_all_items(db: DBClient, monkeypatch, tmp_path):
    first_path = tmp_path / "first.mp4"
    second_path = tmp_path / "second.mp4"
    first_path.touch()
    second_path.touch()
    cfg = CliConfig()
    cfg.organizer.media_sources = {"movies": [str(tmp_path)], "tv": [], "music": []}
    monkeypatch.setattr("mm.server.organizer_sources.load_cli_config", lambda: cfg)
    monkeypatch.setattr(
        "mm.server.routers.organizer.AuthorizedMediaPath.resolve",
        lambda *_args, **_kwargs: SimpleNamespace(path=first_path),
    )
    items = db._run(
        persist_scan_items(
            db._client,
            [
                OrganizerItem(path=str(first_path), media_type="movie", title="First"),
                OrganizerItem(path=str(second_path), media_type="movie", title="Second"),
            ],
            mark_missing=False,
        )
    )

    body = OrganizerItemsPatchBody(
        items=[
            OrganizerItemPatchRequest(
                item_uid=items[0].item_uid,
                revision=items[0].revision,
                title="Changed First",
            ),
            OrganizerItemPatchRequest(
                item_uid=items[1].item_uid,
                revision=items[1].revision + 1,
                title="Changed Second",
            ),
        ]
    )
    with pytest.raises(Exception, match="revision conflict"):
        db._run(patch_items(body, db=db._client))

    rows = db._run(
        db._client.objects.fetchall(OrganizerMediaModel.select().order_by(OrganizerMediaModel.path))
    )
    assert [row.title for row in rows] == ["First", "Second"]


def test_stale_scan_does_not_overwrite_newer_projection_patch(db: DBClient, monkeypatch, tmp_path):
    media_path = tmp_path / "movie.mkv"
    media_path.touch()
    cfg = CliConfig()
    cfg.organizer.media_sources = {"movies": [str(tmp_path)], "tv": [], "music": []}
    monkeypatch.setattr("mm.server.organizer_sources.load_cli_config", lambda: cfg)
    original = OrganizerItem(path=str(media_path), media_type="movie", title="Scanned")
    persisted = db._run(persist_scan_items(db._client, [original], mark_missing=False))[0]
    stale_row = db._run(db._client.objects.get(OrganizerMediaModel, item_uid=persisted.item_uid))
    db._run(
        db._client.objects.execute(
            OrganizerMediaModel.update(title="User edit", revision=2).where(
                OrganizerMediaModel.item_uid == persisted.item_uid
            )
        )
    )

    async def stale_rows(*_args, **_kwargs):
        return {str(media_path): stale_row}

    monkeypatch.setattr(
        "mm.server.organizer_persistence._existing_organizer_rows",
        stale_rows,
    )

    db._run(persist_scan_items(db._client, [original], mark_missing=False))

    row = db._run(db._client.objects.get(OrganizerMediaModel, item_uid=persisted.item_uid))
    assert row.title == "User edit"
    assert row.revision == 2
    assert row.missing == 0
