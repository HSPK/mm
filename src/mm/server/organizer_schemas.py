from __future__ import annotations

from typing import Any

from pydantic import BaseModel as PydanticBase
from pydantic import Field


class OrganizerScanBody(PydanticBase):
    paths: list[str]
    recursive: bool = False


class OrganizerArtworkAsset(PydanticBase):
    kind: str
    path: str
    label: str
    width: int | None = None
    height: int | None = None


class OrganizerFileAsset(PydanticBase):
    kind: str
    path: str
    name: str
    extension: str = ""
    size: int | None = None


class OrganizerStreamInfo(PydanticBase):
    source: str = "internal"
    codec: str = ""
    channels: str = ""
    bit_rate: int | None = None
    bit_depth: int | None = None
    language: str = ""
    default: bool = False
    forced: bool = False
    title: str = ""
    format: str = ""


class OrganizerMediaInfo(PydanticBase):
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str = ""
    video_codec: str = ""
    frame_rate: float | None = None
    video_bit_rate: int | None = None
    video_bit_depth: int | None = None
    hdr_format: str = ""
    audio_streams: list[OrganizerStreamInfo] = Field(default_factory=list)
    subtitle_streams: list[OrganizerStreamInfo] = Field(default_factory=list)


class OrganizerItem(PydanticBase):
    path: str
    item_uid: str | None = None
    revision: int | None = None
    playback_id: str | None = None
    media_type: str
    title: str
    artist: str | None = None
    album_artist: str | None = None
    album: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_end: int | None = None
    disc: int | None = None
    track: int | None = None
    parse_template: str | None = None
    parse_relative_path: str | None = None
    confidence: float = 0.0
    duration: float | None = None
    mime_type: str | None = None
    is_new: bool = False
    metadata: bool = False
    metadata_title: str | None = None
    metadata_title_variants: dict[str, str] = Field(default_factory=dict)
    metadata_artist_variants: dict[str, str] = Field(default_factory=dict)
    metadata_album_artist_variants: dict[str, str] = Field(default_factory=dict)
    metadata_album_variants: dict[str, str] = Field(default_factory=dict)
    metadata_original_title: str | None = None
    metadata_show_title: str | None = None
    metadata_year: int | None = None
    metadata_premiered: str | None = None
    metadata_certification: str | None = None
    metadata_runtime: int | None = None
    metadata_genres: list[str] = Field(default_factory=list)
    metadata_styles: list[str] = Field(default_factory=list)
    metadata_composers: list[str] = Field(default_factory=list)
    metadata_status: str | None = None
    metadata_countries: list[str] = Field(default_factory=list)
    metadata_tagline: str | None = None
    metadata_plot: str | None = None
    metadata_lyrics: str | None = None
    metadata_synced_lyrics: str | None = None
    metadata_tags: list[str] = Field(default_factory=list)
    metadata_ids: dict[str, str] = Field(default_factory=dict)
    metadata_rating: float | None = None
    metadata_rating_source: str | None = None
    metadata_studios: list[str] = Field(default_factory=list)
    metadata_cast: list[str] = Field(default_factory=list)
    images: bool = False
    cover_path: str | None = None
    artwork: list[OrganizerArtworkAsset] = Field(default_factory=list)
    subtitles: bool = False
    lyrics: bool = False
    related_files: list[OrganizerFileAsset] = Field(default_factory=list)
    media_info: OrganizerMediaInfo | None = None


class OrganizerScanResponse(PydanticBase):
    items: list[OrganizerItem]


class OrganizerItemsResponse(PydanticBase):
    items: list[OrganizerItem]


class OrganizerRevealDirectoryBody(PydanticBase):
    item_uids: list[str] = Field(min_length=1)


class OrganizerDetailsBody(PydanticBase):
    items: list[OrganizerItem]


class OrganizerItemPatch(PydanticBase):
    revision: int
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    metadata_title: str | None = None
    metadata_original_title: str | None = None
    metadata_show_title: str | None = None
    metadata_premiered: str | None = None
    metadata_certification: str | None = None
    metadata_runtime: int | None = None
    metadata_genres: list[str] | None = None
    metadata_status: str | None = None
    metadata_countries: list[str] | None = None
    metadata_tagline: str | None = None
    metadata_plot: str | None = None
    metadata_tags: list[str] | None = None
    metadata_ids: dict[str, str] | None = None
    metadata_rating: float | None = None
    metadata_rating_source: str | None = None
    metadata_studios: list[str] | None = None
    metadata_cast: list[str] | None = None
    write_nfo: bool = False


class OrganizerItemPatchRequest(OrganizerItemPatch):
    item_uid: str


class OrganizerItemsPatchBody(PydanticBase):
    items: list[OrganizerItemPatchRequest]


class OrganizerItemsPatchResponse(PydanticBase):
    items: list[OrganizerItem]


class OrganizerMatchBody(PydanticBase):
    items: list[OrganizerItem]
    source: str | None = None
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=32,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    limit: int = 3


class OrganizerCandidate(PydanticBase):
    source: str
    source_id: str
    media_type: str
    title: str
    original_title: str = ""
    show_title: str = ""
    artist: str = ""
    album_artist: str = ""
    album: str = ""
    year: int | None = None
    disc: int | None = None
    track: int | None = None
    overview: str = ""
    tagline: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    logo_url: str = ""
    trailer_url: str = ""
    release_date: str = ""
    certification: str = ""
    runtime: int | None = None
    status: str = ""
    original_language: str = ""
    genres: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    composers: list[str] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)
    cast: list[dict[str, str]] = Field(default_factory=list)
    crew: list[dict[str, str]] = Field(default_factory=list)
    lyrics: str = ""
    synced_lyrics: str = ""
    rating: float | None = None
    confidence: float = 0.0
    title_variants: dict[str, str] = Field(default_factory=dict)
    artist_variants: dict[str, str] = Field(default_factory=dict)
    album_artist_variants: dict[str, str] = Field(default_factory=dict)
    album_variants: dict[str, str] = Field(default_factory=dict)


class OrganizerMatchResult(PydanticBase):
    item: OrganizerItem
    candidates: list[OrganizerCandidate]


class OrganizerMatchResponse(PydanticBase):
    results: list[OrganizerMatchResult]


class OrganizerLyricsSearchBody(PydanticBase):
    path: str
    title: str
    artist: str = ""
    album: str = ""
    source: str = "lrclib"
    limit: int = 5


class OrganizerLyricsCandidate(PydanticBase):
    source: str = "lrclib"
    source_id: str
    title: str
    artist: str = ""
    album: str = ""
    duration: float | None = None
    lyrics: str = ""
    synced_lyrics: str = ""
    confidence: float = 0.0


class OrganizerLyricsSearchResponse(PydanticBase):
    candidates: list[OrganizerLyricsCandidate]


class OrganizerLyricsApplyBody(PydanticBase):
    path: str
    lyrics: str = ""
    synced_lyrics: str = ""
    overwrite: bool = True


class OrganizerPlanBody(PydanticBase):
    items: list[OrganizerItem]
    root: str | None = None
    source: str | None = None
    overwrite: bool = False
    selected_candidates: dict[str, OrganizerCandidate] = Field(default_factory=dict)


class OrganizerRenameOperation(PydanticBase):
    source: str
    target: str
    media_type: str
    status: str
    reason: str = ""


class OrganizerRenamePlanResponse(PydanticBase):
    root: str
    operations: list[OrganizerRenameOperation]
    ready: int
    conflicts: int


class OrganizerNfoOperation(PydanticBase):
    target: str
    media_type: str
    status: str
    reason: str = ""


class OrganizerNfoPlanResponse(PydanticBase):
    operations: list[OrganizerNfoOperation]


class OrganizerArtworkOperation(PydanticBase):
    source_url: str
    target: str
    media_type: str
    status: str
    reason: str = ""


class OrganizerArtworkPlanResponse(PydanticBase):
    operations: list[OrganizerArtworkOperation]


class OrganizerApplyResponse(PydanticBase):
    affected: int
    message: str
    batch_id: str | None = None
    nfo_affected: int = 0
    lyrics_affected: int = 0
    artwork_affected: int = 0


class OrganizerRenameLogEntry(PydanticBase):
    batch_id: str
    created_at: str
    count: int
    status: str


class OrganizerScrapeJobBody(PydanticBase):
    items: list[OrganizerItem]
    source: str | None = None
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=32,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    overwrite: bool = True
    selected_candidates: dict[str, OrganizerCandidate] = Field(default_factory=dict)


class OrganizerJobResponse(PydanticBase):
    id: str
    kind: str
    status: str
    progress: int
    title: str
    message: str
    detail: str = ""
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    created_at: str
    updated_at: str


class JobEventResponse(PydanticBase):
    id: int
    job_id: str
    status: str
    progress: int
    message: str
    detail: str = ""
    error: str = ""
    created_at: str


class OrganizerSourceStatus(PydanticBase):
    name: str
    enabled: bool
    implemented: bool
    has_credentials: bool
    base_url: str
    priority: int


class OrganizerLibraryEntry(PydanticBase):
    key: str
    media_type: str
    title: str
    subtitle: str = ""
    count: int = 0
    cover_id: int | None = None
    year: int | None = None
    artist: str | None = None
    album: str | None = None
    paths: list[str] = Field(default_factory=list)


class OrganizerLibraryResponse(PydanticBase):
    movies: list[OrganizerLibraryEntry] = []
    tv: list[OrganizerLibraryEntry] = []
    music: list[OrganizerLibraryEntry] = []


class OrganizerConfigResponse(PydanticBase):
    language: str
    chinese_script: str = "simplified"
    lyrics_source: str = "lrclib"
    timeout: float
    order: list[str]
    sources: list[OrganizerSourceStatus]
    templates: dict[str, str]
    default_scrapers: dict[str, str] = Field(default_factory=dict)
    media_sources: dict[str, list[str]] = Field(default_factory=dict)


class OrganizerConfigPatch(PydanticBase):
    language: str | None = None
    chinese_script: str | None = None
    lyrics_source: str | None = None
    timeout: float | None = None
    order: list[str] | None = None
    source: str | None = None
    enabled: bool | None = None
    base_url: str | None = None
    priority: int | None = None
    credentials: dict[str, str] | None = None
    templates: dict[str, str] | None = None
    default_scrapers: dict[str, str] | None = None
    media_sources: dict[str, list[str]] | None = None


class OrganizerArtworkBatchBody(PydanticBase):
    playback_ids: list[str]
    size: int = 320


class OrganizerArtworkBatchItem(PydanticBase):
    playback_id: str
    thumb_url: str | None = None
    image_url: str | None = None


class OrganizerArtworkBatchResponse(PydanticBase):
    items: list[OrganizerArtworkBatchItem] = Field(default_factory=list)
