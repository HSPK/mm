"""Organise media files into a directory structure using templates."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from uom.config import DEFAULT_IMPORT_TEMPLATE
from uom.core.scanner import file_hash
from uom.db.dto import Media, Metadata


@dataclass
class ImportAction:
    """Represents a planned file move/copy."""

    source: Path
    destination: Path
    skipped: bool = False
    reason: str = ""


def build_dest_path(
    media: Media,
    metadata: Metadata | None,
    template: str,
    dest_root: Path,
    tags: list[str] | None = None,
) -> Path:
    """Resolve a template into a concrete destination path."""
    from datetime import datetime

    dt = metadata.date_taken if metadata else None
    if dt is None:
        # Fallback to file modified time
        dt = media.modified_at or datetime.now()

    tag_list = tags or []

    values = {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "camera_make": (metadata.camera_make if metadata else "") or "unknown",
        "camera_model": (metadata.camera_model if metadata else "") or "unknown",
        "camera": (metadata.camera_model if metadata else "") or "unknown",
        "lens": (metadata.lens_model if metadata else "") or "unknown",
        "type": media.media_type.value,
        "ext": media.extension,
        "original_name": Path(media.filename).stem,
        "tags": tag_list,
    }

    try:
        rel = template.format_map(_SafeDict(values))
    except (KeyError, IndexError):
        # Fallback: use default template
        rel = DEFAULT_IMPORT_TEMPLATE.format_map(_SafeDict(values))

    return dest_root / rel


class _SafeDict(dict):  # type: ignore[type-arg]
    """dict subclass that returns placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def plan_import(
    media_list: list[tuple[Media, Metadata | None, list[str]]],
    dest_root: Path,
    template: str = DEFAULT_IMPORT_TEMPLATE,
) -> list[ImportAction]:
    """Build a list of planned file operations without executing them."""
    actions: list[ImportAction] = []
    used_paths: set[Path] = set()

    for media, metadata, tags in media_list:
        src = Path(media.path)
        if not src.exists():
            actions.append(
                ImportAction(source=src, destination=src, skipped=True, reason="source missing")
            )
            continue

        dest = build_dest_path(media, metadata, template, dest_root, tags)

        # Handle conflicts
        if dest.exists() or dest in used_paths:
            # Check if it's the same file by hash
            if dest.exists():
                try:
                    if file_hash(src) == file_hash(dest):
                        actions.append(
                            ImportAction(
                                source=src, destination=dest, skipped=True, reason="already exists"
                            )
                        )
                        continue
                except OSError:
                    pass
            # Rename with counter
            stem = dest.stem
            suffix = dest.suffix
            parent = dest.parent
            counter = 1
            while dest.exists() or dest in used_paths:
                dest = parent / f"{stem}_{counter}{suffix}"
                counter += 1

        used_paths.add(dest)
        actions.append(ImportAction(source=src, destination=dest))

    return actions


def execute_import(
    actions: list[ImportAction],
    move: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Execute planned file operations.  Returns count of files moved/copied."""
    pending = [a for a in actions if not a.skipped]
    count = 0

    for i, action in enumerate(pending):
        action.destination.parent.mkdir(parents=True, exist_ok=True)
        if move:
            shutil.move(str(action.source), str(action.destination))
        else:
            shutil.copy2(str(action.source), str(action.destination))
        count += 1
        if on_progress:
            on_progress(i + 1, len(pending))

    return count
