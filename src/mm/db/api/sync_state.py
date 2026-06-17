"""Persisted filesystem state used by library sync."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from peewee import EXCLUDED

if TYPE_CHECKING:
    import peewee_aio

from mm.db.api._source import DbApi
from mm.db.dto import FileSyncState
from mm.db.helpers import to_file_sync_state
from mm.db.models import FileSyncStateModel


class SyncStateApi(DbApi):
    objects: peewee_aio.Manager

    async def snapshot(self) -> dict[str, FileSyncState]:
        rows = await self.objects.fetchall(FileSyncStateModel.select())
        return {row.path: to_file_sync_state(row) for row in rows}

    async def upsert_many(
        self,
        states: list[FileSyncState],
        *,
        batch_size: int = 500,
    ) -> int:
        if not states:
            return 0

        now = dt.datetime.now()
        saved = 0
        for i in range(0, len(states), batch_size):
            chunk = states[i : i + batch_size]
            rows = [
                {
                    "path": state.path,
                    "media": state.media_id,
                    "file_size": state.file_size,
                    "mtime_ns": state.mtime_ns,
                    "file_hash": state.file_hash,
                    "last_seen_scan_id": state.last_seen_scan_id,
                    "last_scanned_at": state.last_scanned_at or now,
                }
                for state in chunk
            ]
            await self.objects.execute(
                FileSyncStateModel.insert_many(rows).on_conflict(
                    conflict_target=[FileSyncStateModel.path],
                    update={
                        FileSyncStateModel.media: EXCLUDED.media_id,
                        FileSyncStateModel.file_size: EXCLUDED.file_size,
                        FileSyncStateModel.mtime_ns: EXCLUDED.mtime_ns,
                        FileSyncStateModel.file_hash: EXCLUDED.file_hash,
                        FileSyncStateModel.last_seen_scan_id: EXCLUDED.last_seen_scan_id,
                        FileSyncStateModel.last_scanned_at: EXCLUDED.last_scanned_at,
                    },
                )
            )
            saved += len(chunk)
        return saved

    async def delete_paths(self, paths: list[str], *, batch_size: int = 500) -> int:
        if not paths:
            return 0

        deleted = 0
        for i in range(0, len(paths), batch_size):
            chunk = paths[i : i + batch_size]
            deleted += await self.objects.execute(
                FileSyncStateModel.delete().where(FileSyncStateModel.path.in_(chunk))
            )
        return deleted
