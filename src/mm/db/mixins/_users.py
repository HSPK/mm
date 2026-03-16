"""User CRUD mixin."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import peewee_aio

from mm.db.dto import User
from mm.db.helpers import hash_password, to_user, verify_password
from mm.db.models import UserModel


class UsersMixin:
    objects: peewee_aio.Manager

    async def verify_user(self, username: str, password: str) -> User | None:
        try:
            u = await self.objects.get(UserModel, username=username)
        except UserModel.DoesNotExist:
            return None
        return to_user(u) if verify_password(password, u.password_hash) else None

    async def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        is_admin: bool = False,
    ) -> User:
        u = await self.objects.create(
            UserModel,
            username=username,
            password_hash=hash_password(password),
            display_name=display_name or username,
            is_admin=is_admin,
            created_at=dt.datetime.now(),
        )
        return to_user(u)

    async def get_user_by_token(self, token: str) -> User | None:
        try:
            return to_user(await self.objects.get(UserModel, token=token))
        except UserModel.DoesNotExist:
            return None

    async def get_user_by_username(self, username: str) -> User | None:
        try:
            return to_user(await self.objects.get(UserModel, username=username))
        except UserModel.DoesNotExist:
            return None

    async def generate_token(self, user_id: int) -> str:
        import secrets

        token = secrets.token_hex(32)
        await self.objects.execute(
            UserModel.update(token=token).where(UserModel.id == user_id)
        )
        return token

    async def invalidate_token(self, token: str) -> None:
        await self.objects.execute(
            UserModel.update(token=None).where(UserModel.token == token)
        )

    async def change_password(self, user_id: int, new_password: str) -> None:
        await self.objects.execute(
            UserModel.update(password_hash=hash_password(new_password)).where(
                UserModel.id == user_id
            )
        )

    async def count_users(self) -> int:
        return await self.objects.count(UserModel.select())

    user_count = count_users

    async def list_users(self) -> list[User]:
        return [to_user(u) for u in await self.objects.fetchall(UserModel.select())]

    async def delete_user(self, user_id: int) -> None:
        await self.objects.execute(UserModel.delete().where(UserModel.id == user_id))
