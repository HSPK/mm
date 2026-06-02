from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mm.io import local_storage

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

DEFAULT_DB_NAME = "mm.db"
DEFAULT_IMPORT_TEMPLATE = (
    "{year}/{year}-{month:02d}-{day:02d}/{hour:02d}{minute:02d}{second:02d}{ext}"
)
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"
CLIP_CONFIDENCE_THRESHOLD = 0.25
HASH_CHUNK_SIZE = 8192


# ---------------------------------------------------------------------------
# User config file (~/.config/mm.yaml)
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config"
CONFIG_PATH = CONFIG_DIR / "mm.yaml"


class RegisteredDatabase(BaseModel):
    """One registered media library database."""

    model_config = ConfigDict(extra="ignore")

    path: Path
    name: str = ""


class CliConfig(BaseModel):
    """Application-level user config stored in ``~/.config/mm.yaml``."""

    model_config = ConfigDict(extra="ignore")

    databases: list[RegisteredDatabase] = Field(default_factory=list)
    active: int = -1

    @property
    def active_database(self) -> RegisteredDatabase | None:
        if self.active < 0 or self.active >= len(self.databases):
            return None
        return self.databases[self.active]


def load_cli_config() -> CliConfig:
    """Load the user config from ~/.config/mm.yaml."""
    if not local_storage.exists(CONFIG_PATH):
        return CliConfig()
    with local_storage.open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return CliConfig()
    try:
        return CliConfig.model_validate(data)
    except ValidationError:
        return CliConfig()


def save_cli_config(cfg: CliConfig) -> None:
    """Write the user config to ~/.config/mm.yaml."""
    local_storage.mkdir(CONFIG_DIR)
    with local_storage.open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(
            cfg.model_dump(mode="json"),
            f,
            default_flow_style=False,
            allow_unicode=True,
        )


def get_active_db() -> Path | None:
    """Return the path of the currently active database, or None."""
    cfg = load_cli_config()
    active = cfg.active_database
    return active.path if active else None


def add_database(db_path: Path, name: str | None = None) -> int:
    """Add a database to the config.  Returns its index."""
    cfg = load_cli_config()
    resolved = db_path.resolve()
    for i, entry in enumerate(cfg.databases):
        if entry.path.resolve() == resolved:
            return i
    cfg.databases.append(RegisteredDatabase(path=resolved, name=name or ""))
    if len(cfg.databases) == 1:
        cfg.active = 0
    save_cli_config(cfg)
    return len(cfg.databases) - 1


def set_active_database(index: int) -> Path:
    """Set the active database by index (1-based from user, 0-based internal).

    Raises ValueError if the index is out of range.
    """
    cfg = load_cli_config()
    if index < 0 or index >= len(cfg.databases):
        raise ValueError(f"Invalid index {index + 1}. Have {len(cfg.databases)} database(s).")
    cfg.active = index
    save_cli_config(cfg)
    return cfg.databases[index].path


def remove_database(index: int) -> Path:
    """Remove a database from the config by 0-based index.

    Adjusts the active index accordingly.  Raises ValueError if out of range.
    Returns the path that was removed.
    """
    cfg = load_cli_config()
    if index < 0 or index >= len(cfg.databases):
        raise ValueError(f"Invalid index {index + 1}. Have {len(cfg.databases)} database(s).")
    removed = cfg.databases.pop(index).path
    if cfg.active == index:
        cfg.active = 0 if cfg.databases else -1
    elif cfg.active > index:
        cfg.active -= 1
    save_cli_config(cfg)
    return removed
