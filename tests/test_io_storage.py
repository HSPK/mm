from __future__ import annotations

from pathlib import Path

from mm.io import local_storage


def test_local_storage_file_operations(tmp_path: Path):
    root = tmp_path / "root"
    local_storage.mkdir(root)

    file_path = root / "photo.jpg"
    local_storage.write_bytes(file_path, b"image")

    assert local_storage.exists(file_path)
    assert local_storage.is_file(file_path)
    assert local_storage.get_size(file_path) == 5
    assert local_storage.read_bytes(file_path) == b"image"

    copied = root / "copy.jpg"
    local_storage.copy(file_path, copied)
    assert local_storage.read_bytes(copied) == b"image"

    moved = root / "moved.jpg"
    local_storage.move(copied, moved)
    assert not local_storage.exists(copied)
    assert local_storage.exists(moved)

    replacement = root / "replacement.jpg"
    local_storage.write_bytes(replacement, b"replacement")
    local_storage.replace(replacement, moved)
    assert local_storage.read_bytes(moved) == b"replacement"
    assert not local_storage.exists(replacement)

    files = sorted(
        path.name for path in local_storage.iter_files(root, allowed_extensions={".jpg"})
    )
    assert files == ["moved.jpg", "photo.jpg"]

    local_storage.delete_file(moved)
    assert not local_storage.exists(moved)
