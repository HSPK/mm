"""Tests for the dedup module."""

from __future__ import annotations

from pathlib import Path

from mm.core.dedup import find_hash_duplicates, find_name_duplicates


def test_name_duplicates(tmp_path: Path):
    content = b"\xff\xd8" + b"\x00" * 100
    big_content = b"\xff\xd8" + b"\x00" * 200

    (tmp_path / "photo.jpg").write_bytes(content)
    (tmp_path / "photo.jpeg").write_bytes(big_content)

    pairs = find_name_duplicates(tmp_path)
    assert len(pairs) == 1
    # Keep the larger one (.jpeg = 202 bytes > .jpg = 102 bytes)
    assert pairs[0].keep.suffix == ".jpeg"
    assert pairs[0].remove.suffix == ".jpg"


def test_hash_duplicates(tmp_path: Path):
    content = b"\xff\xd8SAME_CONTENT" + b"\x00" * 100
    (tmp_path / "a.jpg").write_bytes(content)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.jpg").write_bytes(content)

    # Different content file
    (tmp_path / "c.jpg").write_bytes(b"\xff\xd8DIFFERENT")

    pairs = find_hash_duplicates(tmp_path, progress=False)
    assert len(pairs) == 1
    assert pairs[0].reason == "hash-dup"
