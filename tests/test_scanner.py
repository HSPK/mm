"""Basic tests for the scanner module."""

from __future__ import annotations

from pathlib import Path

from mm.db.models import MediaType
from mm.db.sync_client import DBClient
from mm.library.settings import LibraryConfig
from mm.media.scanner import (
    classify_extension,
    discover_media,
    save_media_metadata,
    scan_and_extract,
    scan_file,
)


def test_classify_extension():
    assert classify_extension(".jpg") == MediaType.PHOTO
    assert classify_extension(".mp4") == MediaType.VIDEO
    assert classify_extension(".flac") == MediaType.AUDIO
    assert classify_extension(".xyz") is None


def test_discover_media_skips_hidden(tmp_path: Path):
    # Create media and hidden files
    (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
    (tmp_path / ".hidden.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
    hidden_dir = tmp_path / ".hidden_dir"
    hidden_dir.mkdir()
    (hidden_dir / "nested.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)

    found = list(discover_media(tmp_path))
    names = [p.name for p in found]
    assert "photo.jpg" in names
    assert ".hidden.jpg" not in names
    assert "nested.jpg" not in names


def test_scan_file(tmp_path: Path):
    f = tmp_path / "test.png"
    f.write_bytes(b"\x89PNG" + b"\x00" * 100)
    media = scan_file(f)
    assert media.extension == ".png"
    assert media.media_type == MediaType.PHOTO
    assert media.file_size == 104
    assert len(media.file_hash) == 64  # SHA-256 hex


def test_save_media_metadata_can_store_destination_path(tmp_path: Path, db: DBClient):
    source = tmp_path / "source" / "original.jpg"
    source.parent.mkdir()
    source.write_bytes(b"\xff\xd8" + b"\x00" * 100)

    library_root = tmp_path / "library"
    destination = library_root / "2026" / "renamed.jpg"
    db.library_config.set(LibraryConfig(library_root=library_root, import_template="{type}{ext}"))

    result = scan_and_extract(source)
    media_id = save_media_metadata(db, result.media, result.metadata, media_path=destination)

    media = db.media.get(media_id)
    assert media is not None
    assert media.path == "2026/renamed.jpg"
    assert media.filename == "renamed.jpg"
