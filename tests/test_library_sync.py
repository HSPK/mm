from __future__ import annotations

from pathlib import Path

from mm.db.dto import Metadata
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.library.maintenance import execute_library_sync, plan_library_sync
from mm.library.settings import LibraryConfig
from mm.media.scanner import save_media_metadata, scan_file


def test_library_sync_indexes_new_file_and_persists_state(
    tmp_path: Path,
    db: DBClient,
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    media_path = library / "new.jpg"
    media_path.write_bytes(b"\xff\xd8" + b"new" * 64)
    db.library_config.set(LibraryConfig(library_root=library, import_template="{type}{ext}"))

    plan = plan_library_sync(db, library, storage=local_storage, jobs=1)

    assert plan.stale_ids == []
    assert plan.changed_ids == []
    assert plan.new_paths == [str(media_path.resolve())]

    result = execute_library_sync(
        db,
        plan,
        jobs=1,
        storage=local_storage,
        metadata_mode="pillow",
    )

    assert result.indexed == 1
    media = db.media.by_path("new.jpg")
    assert media is not None
    state = db.sync_state.snapshot()["new.jpg"]
    assert state.media_id == media.id
    assert state.file_size == media_path.stat().st_size

    next_plan = plan_library_sync(db, library, storage=local_storage, jobs=1)
    assert next_plan.stale_ids == []
    assert next_plan.changed_ids == []
    assert next_plan.new_paths == []


def test_library_sync_preserves_media_row_for_moved_file(
    tmp_path: Path,
    db: DBClient,
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    old_path = library / "old.jpg"
    new_path = library / "new.jpg"
    old_path.write_bytes(b"\xff\xd8" + b"same-content" * 32)
    db.library_config.set(LibraryConfig(library_root=library, import_template="{type}{ext}"))

    media = scan_file(old_path, storage=local_storage)
    media_id = save_media_metadata(db, media, Metadata(), media_path=old_path)
    old_path.rename(new_path)

    plan = plan_library_sync(db, library, storage=local_storage, jobs=1)

    assert plan.stale_ids == [media_id]
    assert plan.new_paths == [str(new_path.resolve())]

    result = execute_library_sync(
        db,
        plan,
        jobs=1,
        storage=local_storage,
        metadata_mode="pillow",
    )

    assert result.moved == 1
    assert result.deleted == 0
    assert db.media.count() == 1
    moved = db.media.get(media_id)
    assert moved is not None
    assert moved.path == "new.jpg"
    assert db.sync_state.snapshot()["new.jpg"].media_id == media_id
