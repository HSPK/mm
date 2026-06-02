from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from mm.db.dto import Media, Metadata
from mm.errors import ImportTemplateError
from mm.media.importer import ImportPlanItem, build_dest_path, execute_import, plan_import


class _PlanStorage:
    def __init__(self, existing: set[Path]) -> None:
        self.existing = {path.resolve() for path in existing}

    def exists(self, path: str | Path) -> bool:
        return Path(path).resolve() in self.existing


class _ExecuteStorage:
    def __init__(self) -> None:
        self.created_dirs: list[Path] = []
        self.copied: list[tuple[Path, Path]] = []
        self.moved: list[tuple[Path, Path]] = []

    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        self.created_dirs.append(Path(path))

    def copy(self, source: str | Path, destination: str | Path) -> None:
        self.copied.append((Path(source), Path(destination)))

    def move(self, source: str | Path, destination: str | Path) -> None:
        self.moved.append((Path(source), Path(destination)))


def test_build_dest_path_uses_supported_values_and_default_date(tmp_path: Path):
    media = Media(filename="ignored.jpg", extension=".jpg", modified_at=dt.datetime(1999, 1, 1))
    metadata = Metadata(camera_model="X100")

    path = build_dest_path(
        media,
        metadata,
        "{year}/{month:02d}/{day:02d}/{hour:02d}{minute:02d}{second:02d}-{camera}-{type}{ext}",
        tmp_path,
        default_date=dt.datetime(2026, 6, 2, 3, 4, 5),
    )

    assert path == tmp_path / "2026/06/02/030405-X100-photo.jpg"


def test_build_dest_path_metadata_date_wins_over_default_date(tmp_path: Path):
    media = Media(filename="ignored.jpg", extension=".jpg")
    metadata = Metadata(date_taken=dt.datetime(2025, 1, 2, 3, 4, 5))

    path = build_dest_path(media, metadata, "{year}-{month:02d}-{day:02d}{ext}", tmp_path)

    assert path == tmp_path / "2025-01-02.jpg"


def test_build_dest_path_raises_structured_template_error(tmp_path: Path):
    media = Media(filename="ignored.jpg", extension=".jpg")

    with pytest.raises(ImportTemplateError) as exc:
        build_dest_path(media, Metadata(), "{original_name}{ext}", tmp_path)

    error = exc.value
    assert error.code.value == "import_template.format_failed"
    assert error.details["template"] == "{original_name}{ext}"
    assert "original_name" in error.details["error"]
    assert error.details["supported_fields"] == [
        "camera",
        "day",
        "ext",
        "hour",
        "minute",
        "month",
        "second",
        "type",
        "year",
    ]


def test_plan_import_uses_injected_storage(tmp_path: Path):
    source = tmp_path / "source.jpg"
    media = Media(
        path=str(source),
        filename="source.jpg",
        extension=".jpg",
        modified_at=dt.datetime(2026, 1, 2, 3, 4, 5),
    )

    missing = plan_import(
        [(media, Metadata())],
        tmp_path / "library",
        "{year}/{type}{ext}",
        storage=_PlanStorage(existing=set()),
    )
    assert missing[0].skipped
    assert missing[0].reason == "source missing"

    planned = plan_import(
        [(media, Metadata())],
        tmp_path / "library",
        "{year}/{type}{ext}",
        storage=_PlanStorage(existing={source}),
    )
    assert not planned[0].skipped
    assert planned[0].destination == tmp_path / "library" / "2026/photo.jpg"


def test_execute_import_uses_injected_storage(tmp_path: Path):
    storage = _ExecuteStorage()
    source = tmp_path / "source.jpg"
    destination = tmp_path / "library" / "photo.jpg"

    count = execute_import(
        [
            ImportPlanItem(
                media=Media(path=str(source), filename="source.jpg", extension=".jpg"),
                metadata=Metadata(),
                source=source,
                destination=destination,
            )
        ],
        storage=storage,
    )

    assert count == 1
    assert storage.created_dirs == [destination.parent]
    assert storage.copied == [(source, destination)]
    assert storage.moved == []
