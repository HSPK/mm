from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from peewee import EXCLUDED

from mm.config import get_config
from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.organizer.localization import select_localized_name
from mm.server.organizer_schemas import OrganizerItem
from mm.server.organizer_sources import OrganizerSourceResolver


@dataclass(frozen=True)
class OrganizerFileFingerprint:
    file_size: int
    mtime_ns: int
    sidecar_signature: str
    scan_version: int


async def persist_scan_items(
    db: AsyncDBClient,
    items: list[OrganizerItem],
    *,
    mark_missing: bool = False,
    completed_roots: Iterable[Path] = (),
    return_items: bool = True,
    source_resolver: OrganizerSourceResolver | None = None,
    seen_paths: Iterable[str] | None = None,
    file_fingerprints: Mapping[str, OrganizerFileFingerprint] | None = None,
    invalidate_source_kinds: Iterable[str] = (),
) -> list[OrganizerItem]:
    now = dt.datetime.now()
    item_paths = {item.path for item in items}
    observed_paths = set(seen_paths) if seen_paths is not None else set(item_paths)
    resolver = source_resolver or OrganizerSourceResolver.from_config()
    resolved_sources = [resolver.resolve_item(item) for item in items]
    source_kinds = {source.kind for source in resolved_sources} | set(invalidate_source_kinds)
    existing_rows = await _existing_organizer_rows(db, item_paths)
    rows: list[dict[str, object]] = []

    for item, source in zip(items, resolved_sources, strict=True):
        source_kind = source.kind
        music_album_id: str | None = None
        music_artist_id: str | None = None
        music_album_artist_id: str | None = None
        music_track_id: str | None = None
        if source_kind == "music" and item.media_type == "track":
            from mm.server.music_catalog import (
                album_artist_id_for_item,
                album_id_for_item,
                artist_id_for_item,
                track_id_for_item,
            )

        payload = item.model_dump(mode="json")
        existing = existing_rows.get(item.path)
        fingerprint = file_fingerprints.get(item.path) if file_fingerprints else None
        is_new = existing is None
        payload["is_new"] = is_new
        revision = (existing.revision + 1) if existing is not None else 1
        item_uid = (
            existing.item_uid if existing is not None and existing.item_uid else uuid.uuid4().hex
        )
        if source_kind == "music" and item.media_type == "track":
            music_track_id = track_id_for_item(
                item,
                existing_id=getattr(existing, "music_track_id", None),
                item_uid=item_uid,
            )
            music_album_id = album_id_for_item(
                item,
                existing_id=getattr(existing, "music_album_id", None),
            )
            music_artist_id = artist_id_for_item(
                item,
                existing_id=getattr(existing, "music_artist_id", None),
            )
            music_album_artist_id = album_artist_id_for_item(
                item,
                existing_id=getattr(existing, "music_album_artist_id", None),
            )
        payload["item_uid"] = item_uid
        payload["revision"] = revision
        rows.append(
            {
                "path": item.path,
                "item_uid": item_uid,
                "revision": revision,
                "source_root": str(source.root) if source.root else None,
                "source_kind": source_kind,
                "media_type": item.media_type,
                "title": item.title,
                "artist": item.artist,
                "album_artist": item.album_artist,
                "album": item.album,
                "year": item.year,
                "season": item.season,
                "episode": item.episode,
                "disc": item.disc,
                "track": item.track,
                "parse_template": item.parse_template,
                "parse_relative_path": item.parse_relative_path,
                "confidence": item.confidence,
                "audio_duration": item.duration,
                "audio_mime_type": item.mime_type,
                "music_track_id": music_track_id,
                "music_album_id": music_album_id,
                "music_artist_id": music_artist_id,
                "music_album_artist_id": music_album_artist_id,
                "music_title_variants": json.dumps(
                    item.metadata_title_variants,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "music_artist_variants": json.dumps(
                    item.metadata_artist_variants,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "music_album_artist_variants": json.dumps(
                    item.metadata_album_artist_variants,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "music_album_variants": json.dumps(
                    item.metadata_album_variants,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "file_size": (
                    fingerprint.file_size if fingerprint else getattr(existing, "file_size", 0)
                ),
                "mtime_ns": (
                    fingerprint.mtime_ns if fingerprint else getattr(existing, "mtime_ns", 0)
                ),
                "sidecar_signature": (
                    fingerprint.sidecar_signature
                    if fingerprint
                    else getattr(existing, "sidecar_signature", "")
                ),
                "scan_version": (
                    fingerprint.scan_version
                    if fingerprint
                    else getattr(existing, "scan_version", 0)
                ),
                "is_new": 1 if is_new else 0,
                "has_metadata": 1 if item.metadata else 0,
                "has_images": 1 if item.images else 0,
                "has_subtitles": 1 if item.subtitles else 0,
                "has_lyrics": 1 if item.lyrics else 0,
                "payload": json.dumps(payload, ensure_ascii=False),
                "missing": 0,
                "first_seen_at": now,
                "last_seen_at": now,
            }
        )
    for chunk in _chunks(rows, 500):
        update_fields = {
            field: getattr(EXCLUDED, field.column_name)
            for field in (
                OrganizerMediaModel.source_kind,
                OrganizerMediaModel.item_uid,
                OrganizerMediaModel.revision,
                OrganizerMediaModel.source_root,
                OrganizerMediaModel.media_type,
                OrganizerMediaModel.title,
                OrganizerMediaModel.artist,
                OrganizerMediaModel.album_artist,
                OrganizerMediaModel.album,
                OrganizerMediaModel.year,
                OrganizerMediaModel.season,
                OrganizerMediaModel.episode,
                OrganizerMediaModel.disc,
                OrganizerMediaModel.track,
                OrganizerMediaModel.parse_template,
                OrganizerMediaModel.parse_relative_path,
                OrganizerMediaModel.confidence,
                OrganizerMediaModel.audio_duration,
                OrganizerMediaModel.audio_mime_type,
                OrganizerMediaModel.music_track_id,
                OrganizerMediaModel.music_album_id,
                OrganizerMediaModel.music_artist_id,
                OrganizerMediaModel.music_album_artist_id,
                OrganizerMediaModel.music_title_variants,
                OrganizerMediaModel.music_artist_variants,
                OrganizerMediaModel.music_album_artist_variants,
                OrganizerMediaModel.music_album_variants,
                OrganizerMediaModel.file_size,
                OrganizerMediaModel.mtime_ns,
                OrganizerMediaModel.sidecar_signature,
                OrganizerMediaModel.scan_version,
                OrganizerMediaModel.is_new,
                OrganizerMediaModel.has_metadata,
                OrganizerMediaModel.has_images,
                OrganizerMediaModel.has_subtitles,
                OrganizerMediaModel.has_lyrics,
                OrganizerMediaModel.payload,
                OrganizerMediaModel.missing,
                OrganizerMediaModel.last_seen_at,
            )
        }
        await db.objects.execute(
            OrganizerMediaModel.insert_many(chunk).on_conflict(
                conflict_target=[OrganizerMediaModel.path],
                update=update_fields,
                where=(OrganizerMediaModel.revision == EXCLUDED.revision - 1),
            )
        )
    for chunk in _chunks(list(observed_paths), 500):
        await db.objects.execute(
            OrganizerMediaModel.update(missing=0, last_seen_at=now).where(
                OrganizerMediaModel.path.in_(chunk)
            )
        )

    if mark_missing:
        roots = list(completed_roots)
        if not roots:
            raise ValueError("Missing reconciliation requires completed roots")
        for root in roots:
            await db.objects.execute(
                OrganizerMediaModel.update(missing=1, last_seen_at=now).where(
                    (OrganizerMediaModel.source_root == str(root.expanduser().resolve()))
                    & (OrganizerMediaModel.last_seen_at < now)
                )
            )

    if "music" in source_kinds:
        from mm.server.music_catalog import invalidate_music_catalog

        invalidate_music_catalog(str(db.database))

    if not return_items or not item_paths:
        return []
    persisted_rows = await db.objects.fetchall(
        OrganizerMediaModel.select().where(OrganizerMediaModel.path.in_(item_paths))
    )
    by_path = {row.path: item_from_light_row(row) for row in persisted_rows}
    return [by_path[item.path] for item in items if item.path in by_path]


def organizer_item_from_payload(payload: str) -> OrganizerItem:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {}
    return OrganizerItem.model_validate(data)


def compact_item_from_payload(payload: str) -> OrganizerItem:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {}
    data.update(
        {
            "metadata_lyrics": None,
            "metadata_synced_lyrics": None,
            "metadata_plot": None,
            "artwork": [],
            "related_files": [],
            "media_info": None,
        }
    )
    return OrganizerItem.model_validate(data)


def item_from_light_row(row: OrganizerMediaModel) -> OrganizerItem:
    language = get_config().scrapers.language
    title_variants = _json_string_map(getattr(row, "music_title_variants", "{}"))
    artist_variants = _json_string_map(getattr(row, "music_artist_variants", "{}"))
    album_artist_variants = _json_string_map(getattr(row, "music_album_artist_variants", "{}"))
    album_variants = _json_string_map(getattr(row, "music_album_variants", "{}"))
    item = OrganizerItem(
        path=row.path,
        item_uid=row.item_uid,
        revision=row.revision,
        playback_id=str(row.id) if row.id is not None else None,
        media_type=row.media_type,
        title=select_localized_name(title_variants, language, row.title),
        artist=select_localized_name(artist_variants, language, row.artist or "") or None,
        album_artist=select_localized_name(
            album_artist_variants,
            language,
            row.album_artist or row.artist or "",
        )
        or None,
        album=select_localized_name(album_variants, language, row.album or "") or None,
        year=row.year,
        season=row.season,
        episode=row.episode,
        disc=row.disc,
        track=row.track,
        parse_template=row.parse_template,
        parse_relative_path=row.parse_relative_path,
        confidence=row.confidence,
        duration=row.audio_duration,
        mime_type=row.audio_mime_type,
        is_new=bool(row.is_new),
        metadata=bool(row.has_metadata),
        metadata_title_variants=title_variants,
        metadata_artist_variants=artist_variants,
        metadata_album_artist_variants=album_artist_variants,
        metadata_album_variants=album_variants,
        images=bool(row.has_images),
        subtitles=bool(row.has_subtitles),
        lyrics=bool(row.has_lyrics),
    )
    payload = getattr(row, "payload", "")
    if not payload:
        return item
    payload_item = compact_item_from_payload(payload)
    return payload_item.model_copy(
        update={
            "path": item.path,
            "item_uid": item.item_uid,
            "revision": item.revision,
            "playback_id": item.playback_id,
            "media_type": item.media_type,
            "title": item.title,
            "artist": item.artist,
            "album_artist": item.album_artist,
            "album": item.album,
            "year": item.year,
            "season": item.season,
            "episode": item.episode,
            "disc": item.disc,
            "track": item.track,
            "parse_template": item.parse_template,
            "parse_relative_path": item.parse_relative_path,
            "confidence": item.confidence,
            "duration": item.duration,
            "mime_type": item.mime_type,
            "is_new": item.is_new,
            "metadata": item.metadata,
            "metadata_title_variants": item.metadata_title_variants,
            "metadata_artist_variants": item.metadata_artist_variants,
            "metadata_album_artist_variants": item.metadata_album_artist_variants,
            "metadata_album_variants": item.metadata_album_variants,
            "images": item.images,
            "subtitles": item.subtitles,
            "lyrics": item.lyrics,
        }
    )


async def _existing_organizer_rows(
    db: AsyncDBClient, paths: set[str]
) -> dict[str, OrganizerMediaModel]:
    existing: dict[str, OrganizerMediaModel] = {}
    for chunk in _chunks(list(paths), 500):
        rows = await db.objects.fetchall(
            OrganizerMediaModel.select(
                OrganizerMediaModel.path,
                OrganizerMediaModel.item_uid,
                OrganizerMediaModel.revision,
                OrganizerMediaModel.file_size,
                OrganizerMediaModel.mtime_ns,
                OrganizerMediaModel.sidecar_signature,
                OrganizerMediaModel.scan_version,
                OrganizerMediaModel.music_track_id,
                OrganizerMediaModel.music_album_id,
                OrganizerMediaModel.music_artist_id,
                OrganizerMediaModel.music_album_artist_id,
            ).where(OrganizerMediaModel.path.in_(chunk))
        )
        existing.update({row.path: row for row in rows})
    return existing


def _chunks(items: list[object], size: int) -> list[list[object]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _json_string_map(payload: str) -> dict[str, str]:
    try:
        value = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str) and item}
