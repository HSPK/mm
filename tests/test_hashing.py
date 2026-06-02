from __future__ import annotations

from pathlib import Path

from mm.utils.hashing import file_hash, quick_hash


def test_file_hash_and_quick_hash(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")

    assert len(file_hash(path)) == 64
    assert quick_hash(path, num_chunks=1, chunk_size=3) == file_hash(path, chunk_size=3)
