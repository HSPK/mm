from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import Request

import mm.server.routers.library as library_router
import mm.server.routers.music as music_router
from mm.db.models import OrganizerMediaModel
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.organizer.filename import parse_media_filename
from mm.server.media_tickets import issue_media_ticket, verify_media_ticket
from mm.server.music_catalog import (
    album_artist_id_for_item,
    invalidate_music_catalog,
    list_music_albums,
    list_music_artists,
    list_music_tracks,
    track_id_for_item,
)
from mm.server.organizer_persistence import persist_scan_items
from mm.server.organizer_schemas import OrganizerItem
from mm.server.routers.player import audio_playback_source
from mm.server.utils import stream_file


def _track(path: Path, *, title: str, album: str, artist: str, disc: int = 1) -> OrganizerItem:
    return OrganizerItem(
        path=str(path),
        media_type="track",
        title=title,
        album=album,
        artist=artist,
        disc=disc,
        track=1,
        duration=123.5,
        mime_type="audio/flac",
    )


def test_scan_persists_audio_duration_and_mime_type(db: DBClient, tmp_path: Path):
    item = _track(
        tmp_path / "Artist" / "Album" / "01 Song.flac",
        title="Song",
        album="Album",
        artist="Artist",
    )
    db._run(persist_scan_items(db._client, [item], mark_missing=False))

    row = db._run(db._client.objects.get(OrganizerMediaModel, path=item.path))
    assert row.audio_duration == 123.5
    assert row.audio_mime_type == "audio/flac"


def test_music_album_ids_are_opaque_paginated_and_ignore_album_pseudo_items(
    db: DBClient, tmp_path: Path
):
    album = tmp_path / "Artist" / "Album"
    items = [
        _track(album / "Disc I" / "01 One.flac", title="One", album="Album", artist="Artist"),
        _track(
            album / "Disc II" / "01 Two.flac",
            title="Two",
            album="Album",
            artist="Artist",
            disc=2,
        ),
        _track(
            tmp_path / "Other" / "Elsewhere" / "01 Three.flac",
            title="Three",
            album="Elsewhere",
            artist="Other",
        ),
    ]
    db._run(persist_scan_items(db._client, items, mark_missing=False))
    db._run(
        db._client.objects.create(
            OrganizerMediaModel,
            path=str(album / "album.nfo"),
            source_kind="music",
            media_type="album",
            title="Album",
        )
    )

    page = db._run(list_music_albums(db._client, offset=0, limit=1))
    assert page.total == 2
    assert len(page.albums) == 1
    assert page.albums[0].album_id.startswith("album_")
    assert page.albums[0].artist_id.startswith("artist_")
    assert str(tmp_path) not in page.albums[0].album_id
    assert page.albums[0].key == page.albums[0].album_id
    assert page.albums[0].count in {1, 2}

    album_page = db._run(list_music_albums(db._client, query="album"))
    assert album_page.total == 1
    tracks = db._run(list_music_tracks(db._client, album_id=album_page.albums[0].album_id))
    assert [track.title for track in tracks.tracks] == ["One", "Two"]
    assert all("path" not in track.model_dump() for track in tracks.tracks)
    assert all(
        track.duration == 123.5 and track.mime_type == "audio/flac" for track in tracks.tracks
    )


def test_audio_filename_includes_browser_mime_metadata(tmp_path: Path):
    parsed = parse_media_filename(tmp_path / "Artist" / "Album" / "01 Song.FLAC")
    assert parsed is not None
    assert parsed.mime_type == "audio/flac"


def test_music_catalog_snapshot_is_invalidated_after_persistence(db: DBClient, tmp_path: Path):
    first = _track(
        tmp_path / "Artist" / "First" / "01 First.flac",
        title="First",
        album="First",
        artist="Artist",
    )
    db._run(persist_scan_items(db._client, [first], mark_missing=False))
    assert db._run(list_music_albums(db._client)).total == 1

    second = _track(
        tmp_path / "Artist" / "Second" / "01 Second.flac",
        title="Second",
        album="Second",
        artist="Artist",
    )
    db._run(persist_scan_items(db._client, [second], mark_missing=False))

    assert db._run(list_music_albums(db._client)).total == 2


def test_music_entity_ids_survive_path_and_artist_rename(db: DBClient, tmp_path: Path):
    item = _track(
        tmp_path / "Artist" / "Album" / "01 Song.flac",
        title="Song",
        album="Album",
        artist="Artist",
    )
    db._run(persist_scan_items(db._client, [item], mark_missing=False))
    before = db._run(list_music_albums(db._client)).albums[0]
    row = db._run(db._client.objects.get(OrganizerMediaModel, path=item.path))
    db._run(
        db._client.objects.execute(
            OrganizerMediaModel.update(
                path=str(tmp_path / "Renamed Artist" / "Renamed Album" / "01 Song.flac"),
                artist="Renamed Artist",
                album="Renamed Album",
            ).where(OrganizerMediaModel.id == row.id)
        )
    )
    rescanned = item.model_copy(
        update={
            "path": str(tmp_path / "Renamed Artist" / "Renamed Album" / "01 Song.flac"),
            "artist": "Renamed Artist",
            "album": "Renamed Album",
        }
    )
    db._run(persist_scan_items(db._client, [rescanned], mark_missing=False))
    invalidate_music_catalog(str(db._client.database))

    after = db._run(list_music_albums(db._client)).albums[0]
    assert after.album_id == before.album_id
    assert after.artist_id == before.artist_id


def test_localized_music_variants_share_canonical_ids(db: DBClient, tmp_path: Path, monkeypatch):
    from mm.config import CliConfig

    cfg = CliConfig()
    cfg.scrapers.language = "zh-CN"
    monkeypatch.setattr("mm.config.load_cli_config", lambda: cfg)
    external_ids = {
        "musicbrainz_recording": "recording-mbid",
        "musicbrainz_release_group": "release-group-mbid",
        "musicbrainz_artist": "artist-mbid",
    }
    items = [
        _track(
            tmp_path / "English" / "Fantasy" / "01 Silence.flac",
            title="Silence",
            album="Fantasy",
            artist="Jay Chou",
        ).model_copy(
            update={
                "metadata_title_variants": {"en": "Silence"},
                "metadata_artist_variants": {"en": "Jay Chou"},
                "metadata_album_variants": {"en": "Fantasy"},
                "metadata_ids": external_ids,
            }
        ),
        _track(
            tmp_path / "Chinese" / "范特西" / "01 安静.flac",
            title="安静",
            album="范特西",
            artist="周杰伦",
        ).model_copy(
            update={
                "metadata_title_variants": {"zh-CN": "安静"},
                "metadata_artist_variants": {"zh-CN": "周杰伦"},
                "metadata_album_variants": {"zh-CN": "范特西"},
                "metadata_ids": external_ids,
            }
        ),
    ]
    db._run(persist_scan_items(db._client, items, mark_missing=False))

    albums = db._run(list_music_albums(db._client))
    tracks = db._run(list_music_tracks(db._client))

    assert albums.total == 1
    assert albums.albums[0].title == "范特西"
    assert albums.albums[0].artist == "周杰伦"
    assert albums.albums[0].count == 2
    assert albums.albums[0].title_variants == {"en": "Fantasy", "zh-CN": "范特西"}
    assert {track.title for track in tracks.tracks} == {"安静"}
    assert all(
        track.title_variants == {"en": "Silence", "zh-CN": "安静"} for track in tracks.tracks
    )
    assert len({track.track_id for track in tracks.tracks}) == 1
    rows = db._run(db._client.objects.fetchall(OrganizerMediaModel.select()))
    assert len({row.music_album_id for row in rows}) == 1
    assert len({row.music_artist_id for row in rows}) == 1
    assert len({row.music_track_id for row in rows}) == 1

    cfg.scrapers.language = "en-US"
    invalidate_music_catalog(str(db._client.database))
    english_albums = db._run(list_music_albums(db._client))
    english_tracks = db._run(list_music_tracks(db._client))
    assert english_albums.albums[0].title == "Fantasy"
    assert english_albums.albums[0].artist == "Jay Chou"
    assert {track.title for track in english_tracks.tracks} == {"Silence"}
    assert english_albums.albums[0].album_id == albums.albums[0].album_id
    assert {track.track_id for track in english_tracks.tracks} == {
        track.track_id for track in tracks.tracks
    }


def test_generic_album_ids_are_not_used_as_track_identity(tmp_path: Path):
    first = _track(
        tmp_path / "Album" / "01 First.flac",
        title="First",
        album="Album",
        artist="Artist",
    ).model_copy(update={"metadata_ids": {"musicbrainz": "album-id"}})
    second = _track(
        tmp_path / "Album" / "02 Second.flac",
        title="Second",
        album="Album",
        artist="Artist",
    ).model_copy(update={"metadata_ids": {"musicbrainz": "album-id"}})

    assert track_id_for_item(first, item_uid="first") != track_id_for_item(
        second,
        item_uid="second",
    )


def test_compilation_album_uses_separate_album_artist_identity(
    db: DBClient,
    tmp_path: Path,
):
    album = tmp_path / "Various Artists" / "Compilation"
    items = [
        _track(
            album / "01 First.flac",
            title="First",
            album="Compilation",
            artist="Artist A",
        ).model_copy(
            update={
                "album_artist": "Various Artists",
                "metadata_artist_variants": {"en": "Artist A"},
                "metadata_album_artist_variants": {"en": "Various Artists"},
                "metadata_ids": {
                    "musicbrainz_recording": "recording-a",
                    "musicbrainz_release_group": "compilation",
                    "musicbrainz_artist_credit": "artist-a",
                    "musicbrainz_album_artist_credit": "various",
                },
            }
        ),
        _track(
            album / "02 Second.flac",
            title="Second",
            album="Compilation",
            artist="Artist B",
        ).model_copy(
            update={
                "album_artist": "Various Artists",
                "metadata_artist_variants": {"en": "Artist B"},
                "metadata_album_artist_variants": {"en": "Various Artists"},
                "metadata_ids": {
                    "musicbrainz_recording": "recording-b",
                    "musicbrainz_release_group": "compilation",
                    "musicbrainz_artist_credit": "artist-b",
                    "musicbrainz_album_artist_credit": "various",
                },
            }
        ),
    ]
    db._run(persist_scan_items(db._client, items, mark_missing=False))

    albums = db._run(list_music_albums(db._client))
    artists = db._run(list_music_artists(db._client))

    assert albums.total == 1
    assert albums.albums[0].artist == "Various Artists"
    assert albums.albums[0].artist_id == album_artist_id_for_item(items[0])
    assert {artist.name for artist in artists.artists} == {
        "Artist A",
        "Artist B",
        "Various Artists",
    }


def test_lyrics_resource_is_resolved_by_playback_id(tmp_path: Path, monkeypatch):
    track = tmp_path / "song.flac"
    track.write_bytes(b"audio")
    track.with_suffix(".lyrics.txt").write_text("plain lyrics", encoding="utf-8")
    track.with_suffix(".lrc").write_text("[00:01.00]synced lyrics", encoding="utf-8")
    row = OrganizerMediaModel(
        path=str(track), source_kind="music", media_type="track", title="Song"
    )

    async def fake_row(db, playback_id):
        assert playback_id == "7"
        return row

    monkeypatch.setattr(music_router, "_music_track_row", fake_row)
    monkeypatch.setattr(music_router, "allowed_media_source_path", lambda path: True)

    result = asyncio.run(music_router.music_lyrics("7", db=object()))
    assert result.lyrics == "plain lyrics"
    assert result.synced_lyrics == "[00:01.00]synced lyrics"
    assert result.version


def test_audio_source_marks_wma_as_known_unsupported():
    source = audio_playback_source(Path("song.wma"), "7", "audio/x-ms-wma")
    assert source.directly_supported is False
    assert source.known_unsupported is True
    assert "WMA" in source.unsupported_reason


def test_media_ticket_is_scoped_to_library_and_playback_id():
    secret = b"test-secret"
    ticket = issue_media_ticket(
        secret,
        library_id="library-1",
        playback_id="7",
        ttl_seconds=60,
    )
    assert verify_media_ticket(
        secret,
        ticket,
        library_id="library-1",
        playback_id="7",
    )
    assert not verify_media_ticket(
        secret,
        ticket,
        library_id="library-2",
        playback_id="7",
    )
    assert not verify_media_ticket(
        secret,
        ticket,
        library_id="library-1",
        playback_id="8",
    )


def test_library_change_is_published_to_all_subscribers():
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    state = SimpleNamespace(library_generation=2, library_event_subscribers={queue})
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    asyncio.run(library_router._publish_library_change(request, "library-2"))

    assert state.library_generation == 3
    assert queue.get_nowait() == {"generation": 3, "library_id": "library-2"}


def test_stream_file_uses_private_cache_and_validates_ranges(tmp_path: Path):
    file_path = tmp_path / "song.mp3"
    file_path.write_bytes(b"abcdef")
    suffix_request = Request({"type": "http", "headers": [(b"range", b"bytes=-2")]})
    response = stream_file(file_path, suffix_request, storage=local_storage)
    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 4-5/6"
    assert response.headers["cache-control"].startswith("private")

    bad_request = Request({"type": "http", "headers": [(b"range", b"bytes=5-1")]})
    rejected = stream_file(file_path, bad_request, storage=local_storage)
    assert rejected.status_code == 416
    assert rejected.headers["content-range"] == "bytes */6"
