"""Parsing helpers shared by metadata and database adapters."""

from __future__ import annotations

import datetime as dt
from typing import Any

DEFAULT_DATETIME_FORMATS = (
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
)


def parse_datetime(
    value: str | None,
    *,
    formats: tuple[str, ...] = DEFAULT_DATETIME_FORMATS,
) -> dt.datetime | None:
    """Parse common EXIF/ISO/database datetime strings into naive datetimes."""
    if not value:
        return None
    text = value.strip()
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass

    for fmt in formats:
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def safe_float(value: Any) -> float | None:
    """Return ``float(value)`` or None when conversion is not possible."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    """Return ``int(value)`` or None when conversion is not possible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
