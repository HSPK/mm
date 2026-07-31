from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, load_cli_config
from mm.db.client import AsyncDBClient
from mm.db.models import JobModel, OrganizerMediaModel
from mm.music.grouping import music_album_directory, music_album_disc_directories
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.server.job_utils import is_cancel_requested, update_job
from mm.server.organizer_assets import _artwork_files
from mm.server.organizer_items import _light_item_from_parsed
from mm.server.organizer_metadata import OrganizerScanContext, _read_metadata_file
from mm.server.organizer_persistence import (
    OrganizerFileFingerprint,
    persist_scan_items,
)
from mm.server.organizer_scan import iter_media_files
from mm.server.organizer_schemas import OrganizerItem, OrganizerScanBody
from mm.server.organizer_sources import OrganizerSourceResolver

# Parse + read sidecar metadata for files concurrently (the work is disk I/O
# bound). Progress/cancel are checked once per chunk instead of once per file,
# which turns thousands of per-item DB writes into a handful.
_SCAN_CONCURRENCY = 4
_SCAN_CHUNK = 400
_SCAN_VERSION = 9
_SIDECAR_EXTENSIONS = {
    ".ass",
    ".idx",
    ".jpeg",
    ".jpg",
    ".lrc",
    ".nfo",
    ".png",
    ".srt",
    ".ssa",
    ".sub",
    ".txt",
    ".vtt",
    ".webp",
}
_SUBTITLE_DIRECTORIES = {"subs", "subtitle", "subtitles"}
_TV_EPISODE_PATTERN = re.compile(
    r"(?:^|[\s._-])(?:s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DiscoveredMediaFile:
    path: Path
    fingerprint: OrganizerFileFingerprint


async def run_sync_job(db: AsyncDBClient, job_id: str) -> None:
    try:
        row = await db.objects.get(JobModel, id=job_id)
        body = OrganizerScanBody.model_validate_json(row.payload)
        await update_job(db, job_id, status="running", progress=1, message="Scanning sources")
        files = await asyncio.to_thread(_discover_media_files, body.paths, body.recursive)
        discovered = await asyncio.to_thread(_fingerprint_media_files, files)
        changed = await _changed_media_files(db, discovered)
        cfg = load_cli_config()
        resolver = OrganizerSourceResolver.from_config(cfg)
        context = OrganizerScanContext.create(chinese_script=cfg.organizer.chinese_script)
        await asyncio.to_thread(_prime_scan_context, [file.path for file in changed], context)
        items = await _build_scan_items(db, job_id, [file.path for file in changed], context)
        if items is None:
            return  # canceled; status already recorded
        await update_job(
            db,
            job_id,
            message="Saving scan results",
            detail=f"{len(discovered)} item(s), {len(changed)} changed",
            progress=90,
        )
        # API job creation only admits configured roots. A full recursive sync
        # may therefore reconcile precisely those roots, never every item of a
        # shared source kind.
        roots = [Path(path).expanduser().resolve() for path in body.paths]
        configured_roots = {source.root for source in resolver.sources}
        completed_roots = [root for root in roots if root in configured_roots and body.recursive]
        source_kinds = {
            source.kind for source in resolver.sources if source.root in completed_roots
        }
        await persist_scan_items(
            db,
            items,
            mark_missing=bool(completed_roots),
            completed_roots=completed_roots,
            return_items=False,
            source_resolver=resolver,
            seen_paths=(str(file.path) for file in discovered),
            file_fingerprints={str(file.path): file.fingerprint for file in discovered},
            invalidate_source_kinds=source_kinds,
        )
        await update_job(
            db,
            job_id,
            status="done",
            progress=100,
            title="Sync complete",
            message=f"Synced {len(discovered)} item(s)",
            detail="",
            result=json.dumps(
                {
                    "items": len(discovered),
                    "updated": len(items),
                    "unchanged": len(discovered) - len(changed),
                },
                ensure_ascii=False,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - persist job-level failure
        await update_job(
            db,
            job_id,
            status="error",
            progress=100,
            title="Sync failed",
            message=str(exc),
            error=str(exc),
        )


def _discover_media_files(paths: list[str], recursive: bool) -> list[Path]:
    files: dict[str, Path] = {}
    for path in paths:
        for file in iter_media_files(Path(path), recursive=recursive):
            files.setdefault(os.path.normcase(os.path.abspath(file)), file)
    return list(files.values())


def _fingerprint_media_files(files: list[Path]) -> list[DiscoveredMediaFile]:
    directory_signatures = {
        directory: _sidecar_directory_signature(directory)
        for directory in _fingerprint_directories(files)
    }
    discovered: list[DiscoveredMediaFile] = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        signature = hashlib.blake2b(digest_size=16)
        for directory in _sidecar_directories(path):
            signature.update(str(directory).encode())
            signature.update(directory_signatures[directory].encode())
        discovered.append(
            DiscoveredMediaFile(
                path=path,
                fingerprint=OrganizerFileFingerprint(
                    file_size=stat.st_size,
                    mtime_ns=stat.st_mtime_ns,
                    sidecar_signature=signature.hexdigest(),
                    scan_version=_SCAN_VERSION,
                ),
            )
        )
    return discovered


def _fingerprint_directories(files: list[Path]) -> set[Path]:
    return {directory for path in files for directory in _sidecar_directories(path)}


def _sidecar_directories(path: Path) -> tuple[Path, ...]:
    if path.suffix.lower() in VIDEO_EXTENSIONS and _looks_like_tv_episode(path):
        return path.parent, path.parent.parent
    if path.suffix.lower() in AUDIO_EXTENSIONS:
        album_directory = music_album_directory(path)
        if album_directory != path.parent:
            return path.parent, album_directory, *music_album_disc_directories(path)
    return (path.parent,)


def _sidecar_directory_signature(directory: Path) -> str:
    signature = hashlib.blake2b(digest_size=16)
    try:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name.casefold())
    except OSError:
        signature.update(b"unreadable")
        return signature.hexdigest()
    for entry in entries:
        if entry.name.startswith("._"):
            continue
        try:
            if entry.is_dir(follow_symlinks=False):
                if entry.name.casefold() in _SUBTITLE_DIRECTORIES:
                    signature.update(entry.name.encode())
                    signature.update(_sidecar_directory_signature(Path(entry.path)).encode())
                continue
            if Path(entry.name).suffix.lower() not in _SIDECAR_EXTENSIONS:
                continue
            stat = entry.stat(follow_symlinks=False)
        except OSError:
            signature.update(entry.name.encode())
            signature.update(b"unreadable")
            continue
        signature.update(entry.name.encode())
        signature.update(str(stat.st_size).encode())
        signature.update(str(stat.st_mtime_ns).encode())
    return signature.hexdigest()


async def _changed_media_files(
    db: AsyncDBClient,
    files: list[DiscoveredMediaFile],
) -> list[DiscoveredMediaFile]:
    rows_by_path: dict[str, OrganizerMediaModel] = {}
    paths = [str(file.path) for file in files]
    for start in range(0, len(paths), 500):
        rows = await db.objects.fetchall(
            OrganizerMediaModel.select(
                OrganizerMediaModel.path,
                OrganizerMediaModel.file_size,
                OrganizerMediaModel.mtime_ns,
                OrganizerMediaModel.sidecar_signature,
                OrganizerMediaModel.scan_version,
            ).where(OrganizerMediaModel.path.in_(paths[start : start + 500]))
        )
        rows_by_path.update({row.path: row for row in rows})
    return [
        file
        for file in files
        if _fingerprint_changed(rows_by_path.get(str(file.path)), file.fingerprint)
    ]


def _fingerprint_changed(
    row: OrganizerMediaModel | None,
    fingerprint: OrganizerFileFingerprint,
) -> bool:
    return (
        row is None
        or row.file_size != fingerprint.file_size
        or row.mtime_ns != fingerprint.mtime_ns
        or row.sidecar_signature != fingerprint.sidecar_signature
        or row.scan_version != fingerprint.scan_version
    )


def _prime_scan_context(files: list[Path], context: OrganizerScanContext) -> None:
    artwork_directories = {directory for path in files for directory in _sidecar_directories(path)}
    for directory in artwork_directories:
        context.list_children(directory)
        _artwork_files(directory, context)
    metadata_paths = {
        metadata_path for path in files for metadata_path in _shared_metadata_paths(path)
    }
    for metadata_path in metadata_paths:
        _read_metadata_file(metadata_path, context)


def _shared_metadata_paths(path: Path) -> tuple[Path, ...]:
    if path.suffix.lower() in AUDIO_EXTENSIONS:
        return (music_album_directory(path) / "album.nfo",)
    if _looks_like_tv_episode(path):
        return path.parent / "tvshow.nfo", path.parent.parent / "tvshow.nfo"
    return (path.parent / "movie.nfo",)


def _looks_like_tv_episode(path: Path) -> bool:
    return bool(_TV_EPISODE_PATTERN.search(path.stem))


def _parse_and_build(file: Path, context: OrganizerScanContext) -> OrganizerItem | None:
    parsed: ParsedMediaFile | None = parse_media_filename(file)
    return _light_item_from_parsed(parsed, context) if parsed else None


async def _build_scan_items(
    db: AsyncDBClient,
    job_id: str,
    files: list[Path],
    context: OrganizerScanContext,
) -> list[OrganizerItem] | None:
    total = len(files)
    if total == 0:
        return []
    semaphore = asyncio.Semaphore(_SCAN_CONCURRENCY)

    async def build(file: Path) -> OrganizerItem | None:
        async with semaphore:
            return await asyncio.to_thread(_parse_and_build, file, context)

    items: list[OrganizerItem] = []
    done = 0
    for start in range(0, total, _SCAN_CHUNK):
        if await is_cancel_requested(db, job_id):
            await update_job(db, job_id, status="canceled", message="Canceled", progress=100)
            return None
        chunk = files[start : start + _SCAN_CHUNK]
        results = await asyncio.gather(*(build(file) for file in chunk))
        items.extend(item for item in results if item is not None)
        done += len(chunk)
        await update_job(
            db,
            job_id,
            event=False,
            message="Reading media metadata",
            detail=chunk[-1].name,
            progress=int(done / total * 80),
        )
    return items
