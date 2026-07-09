from __future__ import annotations

from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.server.organizer_items import _light_item_from_parsed
from mm.server.organizer_metadata import OrganizerScanContext
from mm.server.organizer_persistence import organizer_item_from_payload, persist_scan_items
from mm.server.organizer_schemas import OrganizerLibraryEntry


def iter_media_files(path: Path, *, recursive: bool) -> list[Path]:
    extensions = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
    if path.is_file():
        return [path] if path.suffix.lower() in extensions else []
    if not path.is_dir():
        return []
    pattern = "**/*" if recursive else "*"
    return [
        candidate
        for candidate in path.glob(pattern)
        if candidate.is_file() and candidate.suffix.lower() in extensions
    ]


def parse_paths(paths: list[Path], *, recursive: bool) -> list[ParsedMediaFile]:
    parsed: list[ParsedMediaFile] = []
    for path in paths:
        for candidate in iter_media_files(path, recursive=recursive):
            item = parse_media_filename(candidate)
            if item:
                parsed.append(item)
    return parsed


def parse_configured_sources(paths: list[str], *, recursive: bool) -> list[ParsedMediaFile]:
    return parse_paths([Path(path).expanduser() for path in paths], recursive=recursive)


def movie_entry_from_parsed(
    parsed: ParsedMediaFile,
    cover_id: int | None = None,
) -> OrganizerLibraryEntry:
    return OrganizerLibraryEntry(
        key=f"movie:{cover_id or parsed.path}",
        media_type="movie",
        title=parsed.title,
        subtitle=str(parsed.year or ""),
        count=1,
        cover_id=cover_id,
        year=parsed.year,
        paths=[str(parsed.path)],
    )


async def refresh_organizer_item(db: AsyncDBClient, path: Path) -> None:
    parsed = parse_media_filename(path)
    if parsed is not None:
        await persist_scan_items(
            db,
            [_light_item_from_parsed(parsed, OrganizerScanContext.create())],
            mark_missing=False,
        )
        return
    try:
        row = await db.objects.get(OrganizerMediaModel, path=str(path))
    except OrganizerMediaModel.DoesNotExist:
        return
    item = organizer_item_from_payload(row.payload).model_copy(update={"lyrics": True})
    await persist_scan_items(db, [item], mark_missing=False)
