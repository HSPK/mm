"""Namespaced database APIs."""

from mm.db.api._source import DbApi, DbSource
from mm.db.api.albums import AlbumsApi
from mm.db.api.config import LibraryConfigApi
from mm.db.api.media import MediaApi
from mm.db.api.metadata import MetadataApi
from mm.db.api.smart_albums import SmartAlbumsApi
from mm.db.api.stats import StatsApi
from mm.db.api.tags import TagsApi
from mm.db.api.users import UsersApi

__all__ = [
    "AlbumsApi",
    "LibraryConfigApi",
    "DbApi",
    "DbSource",
    "MediaApi",
    "MetadataApi",
    "SmartAlbumsApi",
    "StatsApi",
    "TagsApi",
    "UsersApi",
]
