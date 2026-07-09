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
