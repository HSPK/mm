from __future__ import annotations

from pathlib import Path

from mm.utils import (
    fmt_duration,
    fmt_size,
    make_relative_path,
    normalise_tag,
    parse_datetime,
    resolve_media_path,
    safe_float,
    safe_int,
)


def test_formatting_helpers():
    assert fmt_size(512) == "512 B"
    assert fmt_size(2048) == "2.0 KB"
    assert fmt_duration(65) == "1m 5s"
    assert fmt_duration(3661) == "1h 1m 1s"


def test_parsing_helpers():
    assert parse_datetime("2026:06:02 14:30:00")
    assert parse_datetime("2026-06-02T14:30:00Z")
    assert parse_datetime("not a date") is None
    assert safe_int("12") == 12
    assert safe_int("x") is None
    assert safe_float("1.5") == 1.5
    assert safe_float(None) is None


def test_path_and_text_helpers(tmp_path: Path):
    root = tmp_path / "library"
    path = root / "2026" / "photo.jpg"

    assert resolve_media_path("2026/photo.jpg", root) == str(path)
    assert make_relative_path(str(path), root) == "2026/photo.jpg"
    assert normalise_tag(" Family Trip ") == "family-trip"
