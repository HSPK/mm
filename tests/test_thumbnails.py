"""Tests for thumbnail cache namespacing across libraries."""

from __future__ import annotations

from pathlib import Path

import pytest

from mm.config import get_config
from mm.db.dto import Media
from mm.db.models import MediaType
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.library.settings import LibraryConfig
from mm.library.thumbnails import build_thumbnail_cache, thumbnail_cache_stats
from mm.media.thumbnails import (
    cache_dir_for_library,
    get_thumbnail,
)

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def test_cache_dir_for_library_uses_id_as_subdir() -> None:
    base = get_config().paths.thumbs_dir
    a = cache_dir_for_library("lib-a")
    b = cache_dir_for_library("lib-b")
    assert a == base / "lib-a"
    assert b == base / "lib-b"
    assert a != b


def test_cache_dir_for_library_falsy_id_uses_base() -> None:
    base = Path("/tmp/thumbs")
    assert cache_dir_for_library(None, base=base) == base
    assert cache_dir_for_library("", base=base) == base


def _make_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (64, 64), color).save(path, "JPEG")


def test_same_media_id_in_different_libraries_does_not_collide(tmp_path: Path) -> None:
    red_src = tmp_path / "red.jpg"
    blue_src = tmp_path / "blue.jpg"
    _make_image(red_src, (255, 0, 0))
    _make_image(blue_src, (0, 0, 255))

    base = tmp_path / "thumbs"
    lib_a = cache_dir_for_library("lib-a", base=base)
    lib_b = cache_dir_for_library("lib-b", base=base)

    thumb_a = get_thumbnail(
        str(red_src), media_id=1, size="sm", cache_dir=lib_a, storage=local_storage
    )
    thumb_b = get_thumbnail(
        str(blue_src), media_id=1, size="sm", cache_dir=lib_b, storage=local_storage
    )

    assert thumb_a is not None and thumb_b is not None
    assert thumb_a != thumb_b
    assert thumb_a.read_bytes() != thumb_b.read_bytes()


def test_same_library_and_media_id_reuses_cache(tmp_path: Path) -> None:
    src = tmp_path / "red.jpg"
    _make_image(src, (255, 0, 0))
    base = tmp_path / "thumbs"
    lib = cache_dir_for_library("lib-a", base=base)

    first = get_thumbnail(str(src), media_id=1, size="sm", cache_dir=lib, storage=local_storage)
    second = get_thumbnail(str(src), media_id=1, size="sm", cache_dir=lib, storage=local_storage)
    assert first is not None and first == second


def test_build_thumbnail_cache_and_stats(tmp_path: Path, db: DBClient) -> None:
    library_root = tmp_path / "library"
    library_root.mkdir()
    source = library_root / "photo.jpg"
    _make_image(source, (0, 128, 255))
    db.library_config.set(LibraryConfig(library_root=library_root))
    library_id = db.library_config.get().library_id
    media_id = db.media.upsert(
        Media(
            path="photo.jpg",
            filename="photo.jpg",
            extension=".jpg",
            media_type=MediaType.PHOTO,
            file_size=source.stat().st_size,
        )
    )
    cache_base = tmp_path / "thumbs"

    result = build_thumbnail_cache(
        db,
        library_root,
        library_id,
        sizes=["sm"],
        cache_base=cache_base,
        storage=local_storage,
    )
    stats = thumbnail_cache_stats(library_id, cache_base=cache_base, storage=local_storage)

    assert media_id > 0
    assert result.total == 1
    assert result.generated == 1
    assert result.cached == 0
    assert result.failed == 0
    assert stats.file_count == 1
    assert stats.total_size > 0


def test_build_thumbnail_cache_reuses_fresh_cache(tmp_path: Path, db: DBClient) -> None:
    library_root = tmp_path / "library"
    library_root.mkdir()
    source = library_root / "photo.jpg"
    _make_image(source, (128, 0, 255))
    db.library_config.set(LibraryConfig(library_root=library_root))
    library_id = db.library_config.get().library_id
    db.media.upsert(
        Media(
            path="photo.jpg",
            filename="photo.jpg",
            extension=".jpg",
            media_type=MediaType.PHOTO,
            file_size=source.stat().st_size,
        )
    )
    cache_base = tmp_path / "thumbs"

    build_thumbnail_cache(
        db,
        library_root,
        library_id,
        sizes=["sm"],
        cache_base=cache_base,
        storage=local_storage,
    )
    result = build_thumbnail_cache(
        db,
        library_root,
        library_id,
        sizes=["sm"],
        cache_base=cache_base,
        storage=local_storage,
    )

    assert result.generated == 0
    assert result.cached == 1
    assert result.failed == 0
