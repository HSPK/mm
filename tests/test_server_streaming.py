from __future__ import annotations

from pathlib import Path

import mm.server.player_video as player_video
import mm.server.routers.player as player_router
from mm.db.sync_client import DBClient
from mm.server.utils import content_type_for


def test_audio_mime_overrides_are_browser_playable():
    # Safari rejects the non-standard types Python's mimetypes returns for
    # these containers (MEDIA_ERR_SRC_NOT_SUPPORTED / code 4).
    assert content_type_for(Path("song.flac")) == "audio/flac"
    assert content_type_for(Path("song.m4a")) == "audio/mp4"
    assert content_type_for(Path("song.mp3")) == "audio/mpeg"
    assert content_type_for(Path("song.wav")) == "audio/wav"
    assert content_type_for(Path("song.aiff")) == "audio/aiff"


def test_flac_mime_is_case_insensitive():
    assert content_type_for(Path("Song.FLAC")) == "audio/flac"


def test_video_mp4_mime_override():
    assert content_type_for(Path("clip.mp4")) == "video/mp4"


def test_unknown_extension_falls_back():
    assert content_type_for(Path("data.bin")) == "application/octet-stream"


def test_probe_streams_caches_per_file(tmp_path: Path, monkeypatch):
    video = tmp_path / "movie.mkv"
    video.write_bytes(b"fake")
    calls = {"n": 0}

    def fake_uncached(path: Path):
        calls["n"] += 1
        return [{"index": 0, "codec_type": "video", "codec_name": "hevc"}]

    monkeypatch.setattr(player_video, "_FFPROBE", "/usr/bin/ffprobe")
    monkeypatch.setattr(player_video, "_probe_streams_uncached", fake_uncached)
    player_video._PROBE_CACHE.clear()

    first = player_video.probe_streams(video)
    second = player_video.probe_streams(video)

    assert first == second
    assert calls["n"] == 1  # second call served from cache


def test_probe_cache_invalidates_on_change(tmp_path: Path, monkeypatch):
    video = tmp_path / "movie.mkv"
    video.write_bytes(b"a")
    calls = {"n": 0}

    def fake_uncached(path: Path):
        calls["n"] += 1
        return [{"index": 0, "codec_type": "video"}]

    monkeypatch.setattr(player_video, "_FFPROBE", "/usr/bin/ffprobe")
    monkeypatch.setattr(player_video, "_probe_streams_uncached", fake_uncached)
    player_video._PROBE_CACHE.clear()

    player_video.probe_streams(video)
    video.write_bytes(b"much longer content changes size")
    player_video.probe_streams(video)

    assert calls["n"] == 2  # size/mtime change busts the cache


def test_ensure_artifact_builds_once(tmp_path: Path):
    target = tmp_path / "artifact.jpg"
    builds = {"n": 0}

    def builder():
        builds["n"] += 1
        target.write_bytes(b"x")

    player_video._ensure_artifact(target, builder)
    player_video._ensure_artifact(target, builder)

    assert builds["n"] == 1
    assert target.exists()


def test_video_media_info_extracts_codec_hdr_and_frame_rate():
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "hevc",
            "width": 3840,
            "height": 2160,
            "color_transfer": "smpte2084",
            "avg_frame_rate": "24000/1001",
            "bits_per_raw_sample": "10",
        },
        {"index": 1, "codec_type": "audio", "codec_name": "ac3"},
    ]
    info = player_video._video_media_info(streams, 1)
    assert info.video_codec == "hevc"
    assert info.audio_codec == "ac3"
    assert info.width == 3840
    assert info.height == 2160
    assert info.hdr == "HDR10"
    assert info.bit_depth == 10
    assert info.frame_rate is not None and round(info.frame_rate, 2) == 23.98


def test_video_media_info_ignores_cover_art_video_stream():
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "mjpeg",
            "disposition": {"attached_pic": 1},
        },
        {"index": 1, "codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
        {"index": 2, "codec_type": "audio", "codec_name": "aac"},
    ]
    info = player_video._video_media_info(streams, 2)
    assert info.video_codec == "h264"
    assert info.width == 1920


def test_unsupported_reason_flags_container_codec_and_hdr():
    hevc_hdr = player_video.VideoMediaInfo(
        video_codec="hevc", audio_codec="aac", hdr="HDR10", bit_depth=10
    )
    ac3 = player_video.VideoMediaInfo(video_codec="h264", audio_codec="ac3")
    playable = player_video.VideoMediaInfo(video_codec="h264", audio_codec="aac")

    assert "MKV container" in player_video._unsupported_reason(Path("movie.mkv"), playable)
    assert (
        player_video._unsupported_reason(Path("movie.mp4"), hevc_hdr)
        == "HEVC HDR10 video is not supported in this browser"
    )
    assert (
        player_video._unsupported_reason(Path("movie.mp4"), ac3)
        == "AC3 audio is not supported in this browser"
    )
    assert player_video._unsupported_reason(Path("movie.mp4"), playable) == ""


def test_video_playback_source_direct_when_browser_friendly(monkeypatch):
    streams = [
        {"index": 0, "codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
        {"index": 1, "codec_type": "audio", "codec_name": "aac"},
    ]
    monkeypatch.setattr(player_video, "probe_streams", lambda path: streams)

    source = player_video.video_playback_source(Path("movie.mp4"), "pid", ffmpeg=None)

    assert source.mode == "direct"
    assert source.playable is True
    assert source.unsupported_reason == ""
    assert source.media_info is not None and source.media_info.video_codec == "h264"
    assert source.mime_type == "video/mp4"


def test_video_playback_source_unsupported_returns_media_info(monkeypatch):
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "hevc",
            "width": 3840,
            "height": 2160,
            "color_transfer": "smpte2084",
        },
        {"index": 1, "codec_type": "audio", "codec_name": "eac3"},
    ]
    monkeypatch.setattr(player_video, "probe_streams", lambda path: streams)

    source = player_video.video_playback_source(Path("movie.mp4"), "pid", ffmpeg=None)

    assert source.mode == "unsupported"
    assert source.playable is False
    assert "HEVC" in source.unsupported_reason
    assert source.url == ""
    assert source.media_info is not None and source.media_info.hdr == "HDR10"


def test_video_playback_source_uses_prefetched_streams(monkeypatch):
    called = {"n": 0}

    def boom(path):
        called["n"] += 1
        return []

    monkeypatch.setattr(player_video, "probe_streams", boom)
    streams = [
        {"index": 0, "codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
        {"index": 1, "codec_type": "audio", "codec_name": "aac"},
    ]
    source = player_video.video_playback_source(Path("m.mp4"), "pid", None, None, streams)

    assert source.mode == "direct"
    assert source.media_info is not None and source.media_info.video_codec == "h264"
    assert called["n"] == 0  # pre-fetched streams skip ffprobe entirely


def test_probe_streams_cached_persists_and_reuses(db: DBClient, tmp_path: Path, monkeypatch):
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"fake-data")
    calls = {"n": 0}

    def fake_probe(path):
        calls["n"] += 1
        return [{"index": 0, "codec_type": "video", "codec_name": "h264"}]

    monkeypatch.setattr(player_router, "probe_streams", fake_probe)
    async_client = db._client

    first = db._run(player_router._probe_streams_cached(async_client, video, refresh=False))
    second = db._run(player_router._probe_streams_cached(async_client, video, refresh=False))

    assert first == second == [{"index": 0, "codec_type": "video", "codec_name": "h264"}]
    assert calls["n"] == 1  # second call served from the persistent DB cache

    db._run(player_router._probe_streams_cached(async_client, video, refresh=True))
    assert calls["n"] == 2  # refresh forces a re-probe


def test_probe_streams_cached_invalidates_on_file_change(db: DBClient, tmp_path: Path, monkeypatch):
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"a")
    calls = {"n": 0}

    def fake_probe(path):
        calls["n"] += 1
        return [{"index": 0, "codec_type": "video", "codec_name": "h264"}]

    monkeypatch.setattr(player_router, "probe_streams", fake_probe)
    async_client = db._client

    db._run(player_router._probe_streams_cached(async_client, video, refresh=False))
    video.write_bytes(b"a much longer payload that changes the file size")
    db._run(player_router._probe_streams_cached(async_client, video, refresh=False))

    assert calls["n"] == 2  # size/mtime change busts the cached row


def test_reveal_is_local_request_only_allows_localhost():
    from mm.server.file_manager import is_local_request

    def req(host):
        return type("Req", (), {"client": type("C", (), {"host": host})()})()

    assert is_local_request(req("127.0.0.1")) is True
    assert is_local_request(req("::1")) is True
    assert is_local_request(req("192.168.1.10")) is False
    assert is_local_request(type("Req", (), {"client": None})()) is False


def test_reveal_in_file_manager_invokes_command(monkeypatch):
    import mm.server.file_manager as file_manager

    calls: list = []
    monkeypatch.setattr(file_manager.sys, "platform", "darwin")
    monkeypatch.setattr(
        file_manager.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args[0]),
    )
    assert file_manager.open_in_file_manager(Path("/tmp/movie.mkv"), select=True) is True
    assert calls == [["open", "-R", "/tmp/movie.mkv"]]
    calls.clear()
    assert file_manager.open_in_file_manager(Path("/tmp/album")) is True
    assert calls == [["open", "/tmp/album"]]


def test_reveal_in_file_manager_returns_false_on_error(monkeypatch):
    import mm.server.file_manager as file_manager

    def boom(*args, **kwargs):
        raise OSError("no window server")

    monkeypatch.setattr(file_manager.subprocess, "run", boom)
    assert file_manager.open_in_file_manager(Path("/tmp/movie.mkv"), select=True) is False
