"""Smart album mixin."""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import peewee_aio

from uom.db.models import SmartAlbumModel

# ── Lazy seed data loader ─────────────────────────────────
_SEED_ALBUMS = _SEED_ALBUMS_UNSET = object()


def _load_seed_albums() -> list[dict[str, Any]]:
    global _SEED_ALBUMS
    if _SEED_ALBUMS is _SEED_ALBUMS_UNSET:
        from uom.db._seed import DEFAULT_SMART_ALBUMS

        _SEED_ALBUMS = DEFAULT_SMART_ALBUMS
    return _SEED_ALBUMS  # type: ignore[return-value]


class SmartAlbumsMixin:
    objects: peewee_aio.Manager

    async def list_smart_album_definitions(self) -> list[dict[str, Any]]:
        rows = await self.objects.fetchall(
            SmartAlbumModel.select()
            .where(SmartAlbumModel.enabled == 1)
            .order_by(SmartAlbumModel.section, SmartAlbumModel.position)
        )
        return [self._sa_to_dict(r) for r in rows]

    async def list_all_smart_album_definitions(self) -> list[dict[str, Any]]:
        rows = await self.objects.fetchall(
            SmartAlbumModel.select().order_by(SmartAlbumModel.section, SmartAlbumModel.position)
        )
        return [self._sa_to_dict(r) for r in rows]

    async def get_smart_album_definition(self, album_id: int) -> dict[str, Any] | None:
        try:
            return self._sa_to_dict(await self.objects.get(SmartAlbumModel, id=album_id))
        except SmartAlbumModel.DoesNotExist:
            return None

    async def create_smart_album(self, data: dict[str, Any]) -> dict[str, Any]:
        now = dt.datetime.now()
        row = await self.objects.create(
            SmartAlbumModel,
            key=data["key"],
            section=data.get("section", "custom"),
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            icon=data.get("icon", "images"),
            color=data.get("color", ""),
            filters=json.dumps(data.get("filters", {})),
            generator=data.get("generator"),
            generator_config=json.dumps(data.get("generator_config", {})),
            position=data.get("position", 0),
            is_system=data.get("is_system", 0),
            enabled=data.get("enabled", 1),
            created_at=now,
            updated_at=now,
        )
        return self._sa_to_dict(row)

    async def update_smart_album(
        self, album_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            await self.objects.get(SmartAlbumModel, id=album_id)
        except SmartAlbumModel.DoesNotExist:
            return None
        updates: dict[str, Any] = {"updated_at": dt.datetime.now()}
        for f in ("key", "section", "title", "subtitle", "icon", "color", "position", "enabled"):
            if f in data:
                updates[f] = data[f]
        if "filters" in data:
            updates["filters"] = (
                json.dumps(data["filters"])
                if isinstance(data["filters"], dict)
                else data["filters"]
            )
        if "generator" in data:
            updates["generator"] = data["generator"]
        if "generator_config" in data:
            updates["generator_config"] = (
                json.dumps(data["generator_config"])
                if isinstance(data["generator_config"], dict)
                else data["generator_config"]
            )
        await self.objects.execute(
            SmartAlbumModel.update(**updates).where(SmartAlbumModel.id == album_id)
        )
        return await self.get_smart_album_definition(album_id)

    async def delete_smart_album(self, album_id: int) -> bool:
        return (
            await self.objects.execute(
                SmartAlbumModel.delete().where(
                    (SmartAlbumModel.id == album_id) & (SmartAlbumModel.is_system == 0)
                )
            )
        ) > 0

    async def toggle_smart_album(self, album_id: int) -> dict[str, Any] | None:
        try:
            row = await self.objects.get(SmartAlbumModel, id=album_id)
        except SmartAlbumModel.DoesNotExist:
            return None
        await self.objects.execute(
            SmartAlbumModel.update(
                enabled=0 if row.enabled else 1, updated_at=dt.datetime.now()
            ).where(SmartAlbumModel.id == album_id)
        )
        return await self.get_smart_album_definition(album_id)

    async def reset_smart_albums(self) -> int:
        await self.objects.execute(SmartAlbumModel.delete())
        return await self._seed_smart_albums()

    @staticmethod
    def _sa_to_dict(row: SmartAlbumModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "key": row.key,
            "section": row.section,
            "title": row.title,
            "subtitle": row.subtitle or "",
            "icon": row.icon or "images",
            "color": row.color or "",
            "filters": json.loads(row.filters) if row.filters else {},
            "generator": row.generator,
            "generator_config": json.loads(row.generator_config) if row.generator_config else {},
            "position": row.position,
            "is_system": bool(row.is_system),
            "enabled": bool(row.enabled),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def _seed_smart_albums(self) -> int:
        if await self.objects.count(SmartAlbumModel.select()) > 0:
            return 0
        now = dt.datetime.now()
        created = 0
        for d in _load_seed_albums():
            await self.objects.create(
                SmartAlbumModel,
                key=d["key"],
                section=d["section"],
                title=d["title"],
                subtitle=d.get("subtitle", ""),
                icon=d.get("icon", "images"),
                color=d.get("color", ""),
                filters=json.dumps(d.get("filters", {})),
                generator=d.get("generator"),
                generator_config=json.dumps(d.get("generator_config", {})),
                position=d.get("position", 0),
                is_system=1,
                enabled=1,
                created_at=now,
                updated_at=now,
            )
            created += 1
        if created:
            print(f"[uom] Seeded {created} default smart album definitions")
        return created
