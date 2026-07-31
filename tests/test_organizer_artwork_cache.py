from __future__ import annotations

from pathlib import Path

from PIL import Image

from mm.organizer.artwork_cache import artwork_thumbnail, first_artwork_path


def test_artwork_thumbnail_uses_disk_cache(tmp_path: Path):
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    cover = album / "folder.jpg"
    Image.new("RGB", (1200, 1200), "red").save(cover)
    audio = album / "01 - Song.mp3"
    audio.write_text("audio")

    thumb = artwork_thumbnail(cover, 256)
    cached = artwork_thumbnail(cover, 256)

    assert first_artwork_path(audio, "track") == cover
    assert thumb is not None
    assert cached == thumb
    assert thumb.suffix == ".webp"
    assert thumb.exists()
    with Image.open(thumb) as image:
        assert max(image.size) <= 256


def test_artwork_path_by_kind_selects_specific_artwork(tmp_path: Path):
    from mm.organizer.artwork_cache import artwork_path_by_kind

    folder = tmp_path / "Movie (2020)"
    folder.mkdir(parents=True)
    (folder / "poster.jpg").write_text("x")
    (folder / "fanart.jpg").write_text("x")
    (folder / "clearlogo.png").write_text("x")
    movie = folder / "Movie (2020).mkv"
    movie.write_text("video")

    assert artwork_path_by_kind(movie, "movie", "poster").name == "poster.jpg"
    assert artwork_path_by_kind(movie, "movie", "fanart").name == "fanart.jpg"
    assert artwork_path_by_kind(movie, "movie", "clearlogo").name == "clearlogo.png"
    assert artwork_path_by_kind(movie, "movie", "banner") is None


def test_multidisc_track_finds_cover_in_sibling_disc(tmp_path: Path):
    album = tmp_path / "Artist" / "Album"
    first_disc = album / "CD1"
    second_disc = album / "CD2"
    first_disc.mkdir(parents=True)
    second_disc.mkdir()
    cover = first_disc / "CD.jpg"
    Image.new("RGB", (10, 10), "blue").save(cover)
    track = second_disc / "01 Track.mp3"
    track.write_text("audio")

    assert first_artwork_path(track, "track") == cover
