from __future__ import annotations

import shutil
from pathlib import Path

from mm.media.scanner import ScanResult, save_media_metadata, scan_file
from mm.db.dto import Metadata
from mm.db.sync_client import DBClient
from mm.library.settings import LibraryConfig
from mm.utils.media_paths import (
    apply_media_path_repairs,
    delete_missing_media_rows,
    plan_media_path_repairs,
)


def test_media_path_repair_resolves_template_destination(tmp_path: Path, db: DBClient):
    source = tmp_path / "source" / "original.jpg"
    source.parent.mkdir()
    source.write_bytes(b"\xff\xd8" + b"\x00" * 100)

    library_root = tmp_path / "library"
    library_root.mkdir()
    destination = library_root / "photo.jpg"
    shutil.copy2(source, destination)

    db.library_config.set(
        LibraryConfig(library_root=library_root, import_template="{type}{ext}")
    )
    result = ScanResult(media=scan_file(source), metadata=Metadata())
    media_id = save_media_metadata(db, result.media, result.metadata, media_path=source)

    plan = plan_media_path_repairs(db, library_root, "{type}{ext}")

    assert plan.bad_paths == 1
    assert len(plan.updates) == 1
    assert plan.deletions == []
    assert plan.unresolved == []
    assert plan.conflicts == []
    assert plan.updates[0].media_id == media_id
    assert plan.updates[0].new_path == "photo.jpg"
    assert plan.by_method == {"template": 1}

    assert apply_media_path_repairs(db, plan.updates) == 1
    media = db.media.get(media_id)
    assert media is not None
    assert media.path == "photo.jpg"


def test_media_path_repair_deletes_missing_unresolved_source(tmp_path: Path, db: DBClient):
    source = tmp_path / "source" / "missing.jpg"
    source.parent.mkdir()
    source.write_bytes(b"\xff\xd8" + b"\x00" * 100)

    library_root = tmp_path / "library"
    library_root.mkdir()
    db.library_config.set(
        LibraryConfig(library_root=library_root, import_template="{type}{ext}")
    )
    result = ScanResult(media=scan_file(source), metadata=Metadata())
    media_id = save_media_metadata(db, result.media, result.metadata, media_path=source)
    source.unlink()

    plan = plan_media_path_repairs(db, library_root, "{type}{ext}")

    assert plan.updates == []
    assert len(plan.deletions) == 1
    assert plan.deletions[0].media_id == media_id
    assert plan.unresolved == []

    assert delete_missing_media_rows(db, plan.deletions) == 1
    assert db.media.get(media_id) is None
