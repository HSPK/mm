from __future__ import annotations

from pathlib import Path

from mm.db.dto import Metadata
from pydantic import ValidationError

from mm.extractor.metadata import (
    extract_audio_metadata,
    extract_metadata,
    extract_photo_metadata,
    extract_video_metadata,
    get_metadata_extractor,
    register_metadata_extractor,
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
