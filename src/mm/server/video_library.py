from __future__ import annotations

import asyncio
from pathlib import Path

from mm.db.client import AsyncDBClient
from mm.db.models import OrganizerMediaModel
from mm.organizer.artwork_cache import first_artwork_path
from mm.server.organizer_persistence import item_from_light_row, organizer_item_from_payload
from mm.server.organizer_schemas import OrganizerItem


async def list_video_items(db: AsyncDBClient, kind: str) -> list[OrganizerItem]:
    rows = await db.objects.fetchall(
        OrganizerMediaModel.select(
            OrganizerMediaModel.id,
            OrganizerMediaModel.path,
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
        )
        .where(
            (OrganizerMediaModel.source_kind == kind)
            & (OrganizerMediaModel.media_type.in_(["movie", "tv"]))
            & (OrganizerMediaModel.missing == 0)
        )
        .order_by(OrganizerMediaModel.path)
    )
    return await asyncio.to_thread(_video_items_from_rows, rows)


def _video_items_from_rows(rows: list[OrganizerMediaModel]) -> list[OrganizerItem]:
    return [_video_item_from_row(row) for row in rows]


def _video_item_from_row(row: OrganizerMediaModel) -> OrganizerItem:
    item = item_from_light_row(row)
    payload_item = organizer_item_from_payload(row.payload)
    cover_path = first_artwork_path(Path(row.path), row.media_type)
    return item.model_copy(update={
        "cover_path": str(cover_path) if cover_path else item.cover_path,
        "metadata_original_title": payload_item.metadata_original_title,
        "metadata_show_title": payload_item.metadata_show_title,
        "metadata_premiered": payload_item.metadata_premiered,
        "metadata_certification": payload_item.metadata_certification,
        "metadata_runtime": payload_item.metadata_runtime,
        "metadata_genres": payload_item.metadata_genres,
        "metadata_status": payload_item.metadata_status,
        "metadata_countries": payload_item.metadata_countries,
        "metadata_tagline": payload_item.metadata_tagline,
        "metadata_plot": payload_item.metadata_plot,
        "metadata_tags": payload_item.metadata_tags,
        "metadata_ids": payload_item.metadata_ids,
        "metadata_studios": payload_item.metadata_studios,
        "metadata_cast": payload_item.metadata_cast,
    })
