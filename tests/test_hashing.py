from __future__ import annotations

from pathlib import Path

from mm.io import local_storage
from mm.utils.hashing import file_hash, quick_hash


def test_file_hash_and_quick_hash(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")

    assert len(file_hash(path, storage=local_storage)) == 64
    assert quick_hash(
        path, num_chunks=1, chunk_size=3, storage=local_storage
    ) == file_hash(path, chunk_size=3, storage=local_storage)
