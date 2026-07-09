from __future__ import annotations

from pydantic import BaseModel as PydanticBase
from pydantic import Field


class ImportPlanBody(PydanticBase):
    source: str
    move: bool = False
    metadata_mode: str = "exiftool"


class ImportPlanOperation(PydanticBase):
    source: str
    destination: str
    media_type: str
    status: str
    reason: str = ""


class ImportPlanResponse(PydanticBase):
    source: str
    library_root: str
    template: str
    discovered: int
    new_files: int
    intra_duplicates: int
    library_duplicates: int
    importable: int
    errors: int
    operations: list[ImportPlanOperation]


class ImportApplyResponse(PydanticBase):
    file_count: int
    indexed_count: int
    message: str


class FileBrowserEntry(PydanticBase):
    name: str
    path: str
    is_dir: bool
    is_file: bool
    extension: str = ""
    size: int | None = None
    modified_at: float | None = None
    selectable: bool = True


class FileBrowserResponse(PydanticBase):
    path: str
    parent: str | None = None
    roots: list[str] = []
    entries: list[FileBrowserEntry] = []


class ThumbnailTypeStatus(PydanticBase):
    media_type: str
    media_count: int
    expected_files: int
    cached_files: int
    failed_count: int = 0


class ThumbnailBuildBody(PydanticBase):
    videos_only: bool = False
    failed_only: bool = False
    force: bool = False
    sizes: list[str] | None = None


class ThumbnailBuildResponse(PydanticBase):
    total: int
    generated: int
    cached: int
    failed: int
    failed_count: int
    message: str


class ThumbnailStatusResponse(PydanticBase):
    ffmpeg_available: bool
    cache_dir: str
    file_count: int
    total_size: int
    failed_count: int
    by_type: list[ThumbnailTypeStatus] = Field(default_factory=list)
