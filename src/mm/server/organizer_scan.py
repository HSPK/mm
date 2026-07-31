from __future__ import annotations

import os
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
        return [path] if _is_media_file(path, extensions) else []
    if not path.is_dir():
        return []
    files: list[Path] = []
    _scan_media_dir(path, extensions, recursive=recursive, out=files)
    return files


def _scan_media_dir(
    directory: Path,
    extensions: set[str],
    *,
    recursive: bool,
    out: list[Path],
) -> None:
    # os.scandir exposes each entry's type from the single directory read, so we
    # filter by name/extension before ever calling stat(). The old
    # ``path.glob("**/*")`` + ``candidate.is_file()`` stat'd every entry (files
    # *and* directories), which is a syscall storm on network mounts.
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return
    for entry in entries:
        name = entry.name
        if name.startswith("._"):
            continue
        # Recurse only into real subdirectories, never following directory
        # symlinks — mirrors pathlib's ``**`` and avoids symlink cycles.
        if recursive and entry.is_dir(follow_symlinks=False):
            _scan_media_dir(Path(entry.path), extensions, recursive=recursive, out=out)
            continue
        if os.path.splitext(name)[1].lower() in extensions and entry.is_file():
            out.append(Path(entry.path))


def _is_media_file(path: Path, extensions: set[str]) -> bool:
    # Skip AppleDouble sidecars (._foo.mp3) macOS drops on non-HFS volumes;
    # they carry a media extension but are not real media.
    return not path.name.startswith("._") and path.suffix.lower() in extensions


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
