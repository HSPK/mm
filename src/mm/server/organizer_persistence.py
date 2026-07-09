from __future__ import annotations

import datetime as dt
import json

from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.server.organizer_schemas import OrganizerItem
from mm.server.organizer_sources import source_kind_for_item


async def persist_scan_items(
    db: AsyncDBClient,
    items: list[OrganizerItem],
    *,
    mark_missing: bool = True,
) -> list[OrganizerItem]:
    now = dt.datetime.now()
    seen_paths = {item.path for item in items}
    source_kinds = {source_kind_for_item(item) for item in items}
    existing_paths = await _existing_organizer_paths(db, seen_paths)
    result: list[OrganizerItem] = []
    rows: list[dict[str, object]] = []

    for item in items:
        source_kind = source_kind_for_item(item)
        payload = item.model_dump(mode="json")
        payload["is_new"] = item.path not in existing_paths
        rows.append({
            "path": item.path,
            "source_kind": source_kind,
            "media_type": item.media_type,
            "title": item.title,
            "artist": item.artist,
            "album": item.album,
            "year": item.year,
            "season": item.season,
            "episode": item.episode,
            "disc": item.disc,
            "track": item.track,
            "parse_template": item.parse_template,
            "parse_relative_path": item.parse_relative_path,
            "confidence": item.confidence,
            "is_new": 1 if payload["is_new"] else 0,
            "has_metadata": 1 if item.metadata else 0,
            "has_images": 1 if item.images else 0,
            "has_subtitles": 1 if item.subtitles else 0,
            "has_lyrics": 1 if item.lyrics else 0,
            "payload": json.dumps(payload, ensure_ascii=False),
            "missing": 0,
            "first_seen_at": now,
            "last_seen_at": now,
        })
        result.append(OrganizerItem.model_validate(payload))

    for chunk in _chunks(rows, 500):
        await db.objects.execute(
            OrganizerMediaModel.insert_many(chunk).on_conflict(
                conflict_target=[OrganizerMediaModel.path],
                preserve=[
                    OrganizerMediaModel.source_kind,
                    OrganizerMediaModel.media_type,
                    OrganizerMediaModel.title,
                    OrganizerMediaModel.artist,
                    OrganizerMediaModel.album,
                    OrganizerMediaModel.year,
                    OrganizerMediaModel.season,
                    OrganizerMediaModel.episode,
                    OrganizerMediaModel.disc,
                    OrganizerMediaModel.track,
                    OrganizerMediaModel.parse_template,
                    OrganizerMediaModel.parse_relative_path,
                    OrganizerMediaModel.confidence,
                    OrganizerMediaModel.is_new,
                    OrganizerMediaModel.has_metadata,
                    OrganizerMediaModel.has_images,
                    OrganizerMediaModel.has_subtitles,
                    OrganizerMediaModel.has_lyrics,
                    OrganizerMediaModel.payload,
                    OrganizerMediaModel.missing,
                    OrganizerMediaModel.last_seen_at,
                ],
            )
        )

    if mark_missing:
        for source_kind in source_kinds:
            await db.objects.execute(
                OrganizerMediaModel.update(missing=1, last_seen_at=now).where(
                    (OrganizerMediaModel.source_kind == source_kind)
                    & (OrganizerMediaModel.last_seen_at < now)
                )
            )

    return result


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
    data.update({
        "metadata_lyrics": None,
        "metadata_synced_lyrics": None,
        "metadata_plot": None,
        "artwork": [],
        "related_files": [],
        "media_info": None,
    })
    return OrganizerItem.model_validate(data)


def item_from_light_row(row: OrganizerMediaModel) -> OrganizerItem:
    item = OrganizerItem(
        path=row.path,
        playback_id=str(row.id) if row.id is not None else None,
        media_type=row.media_type,
        title=row.title,
        artist=row.artist,
        album=row.album,
        year=row.year,
        season=row.season,
        episode=row.episode,
        disc=row.disc,
        track=row.track,
        parse_template=row.parse_template,
        parse_relative_path=row.parse_relative_path,
        confidence=row.confidence,
        is_new=bool(row.is_new),
        metadata=bool(row.has_metadata),
        images=bool(row.has_images),
        subtitles=bool(row.has_subtitles),
        lyrics=bool(row.has_lyrics),
    )
    payload = getattr(row, "payload", "")
    if not payload:
        return item
    payload_item = compact_item_from_payload(payload)
    return payload_item.model_copy(update={
        "path": item.path,
        "playback_id": item.playback_id,
        "media_type": item.media_type,
        "title": item.title,
        "artist": item.artist,
        "album": item.album,
        "year": item.year,
        "season": item.season,
        "episode": item.episode,
        "disc": item.disc,
        "track": item.track,
        "parse_template": item.parse_template,
        "parse_relative_path": item.parse_relative_path,
        "confidence": item.confidence,
        "is_new": item.is_new,
        "metadata": item.metadata,
        "images": item.images,
        "subtitles": item.subtitles,
        "lyrics": item.lyrics,
    })


async def _existing_organizer_paths(db: AsyncDBClient, paths: set[str]) -> set[str]:
    existing: set[str] = set()
    for chunk in _chunks(list(paths), 500):
        rows = await db.objects.fetchall(
            OrganizerMediaModel.select(OrganizerMediaModel.path).where(
                OrganizerMediaModel.path.in_(chunk)
            )
        )
        existing.update(row.path for row in rows)
    return existing


def _chunks(items: list[object], size: int) -> list[list[object]]:
    return [items[index:index + size] for index in range(0, len(items), size)]
