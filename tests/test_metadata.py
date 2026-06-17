from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from mm.db.dto import Metadata
from mm.extractor.metadata import (
    MetadataToolUnavailable,
    extract_audio_metadata,
    extract_metadata,
    extract_metadata_many,
    extract_photo_metadata,
    extract_photo_metadata_pillow,
    extract_video_metadata,
    get_metadata_extractor,
    register_metadata_extractor,
    require_metadata_mode,
)


def test_registered_metadata_extractors_for_known_extensions():
    assert get_metadata_extractor(Path("photo.jpg")) is extract_photo_metadata
    assert get_metadata_extractor(Path("video.mp4")) is extract_video_metadata
    assert get_metadata_extractor(Path("audio.flac")) is extract_audio_metadata
    assert get_metadata_extractor(Path("unknown.bin")) is extract_photo_metadata


def test_register_metadata_extractor_for_custom_extension():
    def custom_extractor(path: Path, media_id: int) -> Metadata:
        return Metadata(media_id=media_id, camera_model=path.suffix)

    register_metadata_extractor(["custom-meta"], custom_extractor)

    result = extract_metadata(Path("file.custom-meta"), 42)

    assert result.media_id == 42
    assert result.camera_model == ".custom-meta"


def test_register_metadata_extractor_strictly_validates_registration():
    def custom_extractor(path: Path, media_id: int) -> Metadata:
        return Metadata(media_id=media_id)

    try:
        register_metadata_extractor([], custom_extractor)
    except ValidationError as error:
        assert "extensions" in str(error)
    else:
        raise AssertionError("empty extension registration should fail")


def test_extract_metadata_strictly_validates_extractor_output():
    def bad_extractor(path: Path, media_id: int):  # noqa: ANN202
        return {"media_id": media_id}

    register_metadata_extractor(["bad-meta"], bad_extractor)

    try:
        extract_metadata(Path("file.bad-meta"), 1)
    except ValidationError as error:
        assert "metadata" in str(error)
    else:
        raise AssertionError("invalid extractor return type should fail")


def test_exiftool_mode_requires_exiftool(monkeypatch):
    from mm.extractor import metadata as metadata_module

    monkeypatch.setattr(metadata_module, "_EXIFTOOL", None)

    try:
        require_metadata_mode("exiftool")
    except MetadataToolUnavailable as error:
        assert "brew install exiftool" in str(error)
        assert "--metadata-mode pillow" in str(error)
    else:
        raise AssertionError("missing exiftool should abort exiftool mode")


def test_extract_photo_metadata_uses_explicit_pillow_mode(tmp_path: Path, monkeypatch):
    from PIL import Image

    from mm.extractor import metadata as metadata_module

    image_path = tmp_path / "photo.jpg"
    img = Image.new("RGB", (8, 6), (1, 2, 3))
    exif = img.getexif()
    exif[306] = "2026:06:17 11:53:07"
    exif[271] = "SONY"
    exif[272] = "ILCE-7M3"
    img.save(image_path, "JPEG", exif=exif)
    monkeypatch.setattr(metadata_module, "_EXIFTOOL", None)

    result = extract_photo_metadata_pillow(image_path, 7)

    assert result.media_id == 7
    assert result.date_taken is not None
    assert result.date_taken.isoformat(sep=" ") == "2026-06-17 11:53:07"
    assert result.camera_make == "SONY"
    assert result.camera_model == "ILCE-7M3"
    assert result.width == 8
    assert result.height == 6


def test_extract_metadata_many_batches_exiftool(tmp_path: Path, monkeypatch):
    from mm.extractor import metadata as metadata_module

    first = (tmp_path / "a.jpg").resolve()
    second = (tmp_path / "b.jpg").resolve()
    first.write_bytes(b"")
    second.write_bytes(b"")
    calls: list[list[str]] = []

    def fake_run_json_command(command: list[str]):
        calls.append(command)
        return [
            {
                "SourceFile": str(first),
                "EXIF:DateTimeOriginal": "2026:06:17 11:53:07",
                "EXIF:Make": "SONY",
            },
            {
                "SourceFile": str(second),
                "EXIF:DateTimeOriginal": "2026:06:17 11:53:08",
                "EXIF:Make": "SONY",
            },
        ]

    monkeypatch.setattr(metadata_module, "_EXIFTOOL", "/usr/bin/exiftool")
    monkeypatch.setattr(metadata_module, "run_json_command", fake_run_json_command)
    monkeypatch.setattr(metadata_module, "_extract_pillow_photo", lambda _path: {})

    result = extract_metadata_many([first, second], [1, 2])

    assert len(calls) == 1
    assert str(first) in calls[0]
    assert str(second) in calls[0]
    assert [metadata.media_id for metadata in result] == [1, 2]
    dates = [metadata.date_taken.isoformat(sep=" ") for metadata in result if metadata.date_taken]
    assert dates == [
        "2026-06-17 11:53:07",
        "2026-06-17 11:53:08",
    ]
