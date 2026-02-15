"""Global configuration and constants for UOM."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Supported media extensions (lower-case, with leading dot)
# ---------------------------------------------------------------------------

PHOTO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".heic",
        ".heif",
        ".webp",
        ".cr2",
        ".cr3",
        ".nef",
        ".arw",
        ".dng",
        ".orf",
        ".rw2",
        ".raf",
        ".tiff",
        ".tif",
        ".bmp",
    }
)

VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".mts"}
)

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".flac", ".wav", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"}
)

ALL_MEDIA_EXTENSIONS: frozenset[str] = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# ---------------------------------------------------------------------------
# Default CLIP auto-tag vocabulary
# ---------------------------------------------------------------------------

DEFAULT_CLIP_LABELS: list[str] = [
    "landscape",
    "portrait",
    "food",
    "animal",
    "pet",
    "cat",
    "dog",
    "sunset",
    "sunrise",
    "beach",
    "mountain",
    "city",
    "street",
    "indoor",
    "outdoor",
    "night",
    "snow",
    "rain",
    "flower",
    "people",
    "group",
    "selfie",
    "architecture",
    "car",
    "water",
    "forest",
    "sky",
    "cloud",
    "sport",
    "wedding",
    "birthday",
    "travel",
    "concert",
    "art",
    "document",
    "screenshot",
]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_DB_NAME = "uom.db"
DEFAULT_ORGANIZE_TEMPLATE = "{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"
CLIP_CONFIDENCE_THRESHOLD = 0.25
HASH_CHUNK_SIZE = 8192


@dataclass
class UOMConfig:
    """Runtime configuration resolved from CLI flags, env vars, and defaults."""

    db_path: Path = field(default_factory=lambda: Path(os.getenv("UOM_DB", DEFAULT_DB_NAME)))
    organize_template: str = DEFAULT_ORGANIZE_TEMPLATE
    clip_model: str = CLIP_MODEL_NAME
    clip_pretrained: str = CLIP_PRETRAINED
    clip_threshold: float = CLIP_CONFIDENCE_THRESHOLD

    # Computed helpers -------------------------------------------------------

    @property
    def db_uri(self) -> str:
        return str(self.db_path.resolve())
