from __future__ import annotations

from pydantic import BaseModel as PydanticBase
from pydantic import Field


class MusicTrack(PydanticBase):
    track_id: str
    playback_id: str | None = None
    title: str
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    disc: int | None = None
    track: int | None = None
    metadata: bool = False
    images: bool = False
    lyrics: bool = False
    duration: float | None = None
    mime_type: str | None = None
    title_variants: dict[str, str] = Field(default_factory=dict)
    artist_variants: dict[str, str] = Field(default_factory=dict)
    album_variants: dict[str, str] = Field(default_factory=dict)


class MusicAlbum(PydanticBase):
    album_id: str
    artist_id: str
    album_artist_id: str
    key: str
    title: str
    artist: str
    year: int | None = None
    count: int = 0
    cover_playback_id: str | None = None
    title_variants: dict[str, str] = Field(default_factory=dict)
    artist_variants: dict[str, str] = Field(default_factory=dict)


class MusicAlbumsResponse(PydanticBase):
    albums: list[MusicAlbum] = Field(default_factory=list)
    offset: int = 0
    limit: int = 50
    total: int = 0


class MusicTracksResponse(PydanticBase):
    tracks: list[MusicTrack] = Field(default_factory=list)
    offset: int = 0
    limit: int = 100
    total: int = 0


class MusicArtist(PydanticBase):
    artist_id: str
    name: str
    album_count: int = 0
    track_count: int = 0
    cover_playback_id: str | None = None
    name_variants: dict[str, str] = Field(default_factory=dict)


class MusicArtistsResponse(PydanticBase):
    artists: list[MusicArtist] = Field(default_factory=list)
    offset: int = 0
    limit: int = 100
    total: int = 0


class MusicLyricsResource(PydanticBase):
    playback_id: str
    lyrics: str = ""
    synced_lyrics: str = ""
    version: str = ""
