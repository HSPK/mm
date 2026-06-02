"""Text normalization helpers."""

from __future__ import annotations


def normalise_tag(name: str) -> str:
    """Normalize a tag name for consistent storage and lookup."""
    return name.strip().lower().replace(" ", "-")
