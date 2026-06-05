"""Tests for thumbnail cache namespacing across libraries."""

from __future__ import annotations

from pathlib import Path

import pytest

from mm.config import get_config
from mm.io import local_storage
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
