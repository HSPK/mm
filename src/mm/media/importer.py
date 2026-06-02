"""Organise media files into a directory structure using templates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mm.db.dto import Media, Metadata
from mm.errors import ImportTemplateError
from mm.io import FileStorage, local_storage


@dataclass
class ImportPlanItem:
    """Represents a planned file move/copy."""

    media: Media
    metadata: Metadata
    source: Path
    destination: Path
    skipped: bool = False
    reason: str = ""


def build_dest_path(
    media: Media,
    metadata: Metadata,
    template: str,
    dest_root: Path,
    default_date: datetime | None = None,
) -> Path:
    """Resolve a template into a concrete destination path."""
    dt = metadata.date_taken or default_date or datetime.now()

    values = {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "camera": metadata.camera_model or "unknown",
        "type": media.media_type.value,
        "ext": media.extension,
    }

    try:
        rel = template.format_map(values)
    except (AttributeError, IndexError, KeyError, ValueError) as error:
        raise ImportTemplateError(template, values, error) from error

    return dest_root / rel


def plan_import(
    media_list: list[tuple[Media, Metadata]],
    dest_root: Path,
    template: str,
    *,
    storage: FileStorage = local_storage,
) -> list[ImportPlanItem]:
    """Build a list of planned file operations without executing them."""
    plan: list[ImportPlanItem] = []
    used_paths: set[Path] = set()

    for media, metadata in media_list:
        src = Path(media.path)
        if not storage.exists(src):
            plan.append(
                ImportPlanItem(
                    media=media,
                    metadata=metadata,
                    source=src,
                    destination=src,
                    skipped=True,
                    reason="source missing",
                )
            )
            continue

        dest = build_dest_path(
            media,
            metadata,
            template,
            dest_root,
            default_date=media.modified_at,
        )

        # Skip if source and destination resolve to the same file
        if src.resolve() == dest.resolve():
            plan.append(
                ImportPlanItem(
                    media=media,
                    metadata=metadata,
                    source=src,
                    destination=dest,
                    skipped=True,
                    reason="already in place",
                )
            )
            continue

        # Handle path conflicts
        if storage.exists(dest) or dest in used_paths:
            stem = dest.stem
            suffix = dest.suffix
            parent = dest.parent
            counter = 1
            while storage.exists(dest) or dest in used_paths:
                dest = parent / f"{stem}_{counter}{suffix}"
                counter += 1

        used_paths.add(dest)
        plan.append(ImportPlanItem(media=media, metadata=metadata, source=src, destination=dest))

    return plan


def execute_import(
    plan: list[ImportPlanItem],
    move: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
    *,
    storage: FileStorage = local_storage,
) -> int:
    """Execute planned file operations.  Returns count of files moved/copied."""
    pending = [item for item in plan if not item.skipped]
    count = 0

    for i, item in enumerate(pending):
        storage.mkdir(item.destination.parent)
        if move:
            storage.move(item.source, item.destination)
        else:
            storage.copy(item.source, item.destination)
        count += 1
        if on_progress:
            on_progress(i + 1, len(pending))

    return count
