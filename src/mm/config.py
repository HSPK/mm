from __future__ import annotations

import threading
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mm.db.backend import DatabaseTarget
from mm.io import local_storage

# ── Compile-time constants (NOT user-configurable) ──────────────────────────

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


# ── Section defaults ────────────────────────────────────────────────────────

_DEFAULT_IMPORT_TEMPLATE = (
    "{year}/{year}-{month:02d}-{day:02d}/{hour:02d}{minute:02d}{second:02d}{ext}"
)

_DEFAULT_THUMB_SIZES: dict[str, tuple[int, int]] = {
    "sm": (200, 200),
    "md": (400, 400),
    "lg": (800, 800),
    "xl": (1920, 1080),
}

_DEFAULT_CLIP_LABELS: list[str] = [
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


# ── User config file path ───────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config"
CONFIG_PATH = CONFIG_DIR / "mm.yaml"


# ── Section models ──────────────────────────────────────────────────────────


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cache_dir: Path = Path.home() / ".cache" / "mm"

    @property
    def thumbs_dir(self) -> Path:
        return self.cache_dir / "thumbs"

    @property
    def geonames_dir(self) -> Path:
        return self.cache_dir / "geonames"


class ThumbnailConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sizes: dict[str, tuple[int, int]] = Field(default_factory=lambda: dict(_DEFAULT_THUMB_SIZES))
    http_cache_control: str = "public, max-age=31536000, immutable"


class ClipConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_name: str = "ViT-B-32"
    pretrained: str = "openai"
    confidence_threshold: float = 0.25
    labels: list[str] = Field(default_factory=lambda: list(_DEFAULT_CLIP_LABELS))


class HashingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_size: int = 8192


class ImportConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    db_name: str = "mm.db"
    template: str = _DEFAULT_IMPORT_TEMPLATE


class CacheLimits(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ttl: int
    max: int


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token_cache: CacheLimits = Field(default_factory=lambda: CacheLimits(ttl=300, max=256))
    media_path_cache: CacheLimits = Field(default_factory=lambda: CacheLimits(ttl=600, max=4096))


class RegisteredDatabase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str
    name: str = ""


class CliConfig(BaseModel):
    """Top-level application config persisted at ``~/.config/mm.yaml``."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    databases: list[RegisteredDatabase] = Field(default_factory=list)
    active: int = -1

    paths: PathsConfig = Field(default_factory=PathsConfig)
    thumbnails: ThumbnailConfig = Field(default_factory=ThumbnailConfig)
    clip: ClipConfig = Field(default_factory=ClipConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    import_: ImportConfig = Field(default_factory=ImportConfig, alias="import")
    server: ServerConfig = Field(default_factory=ServerConfig)

    @property
    def active_database(self) -> RegisteredDatabase | None:
        if self.active < 0 or self.active >= len(self.databases):
            return None
        return self.databases[self.active]


# ── Loader + module-level cache ─────────────────────────────────────────────

_cached: CliConfig | None = None
_cache_lock = threading.Lock()


def load_cli_config() -> CliConfig:
    """Read ``CONFIG_PATH`` directly, bypassing the cache."""
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
    """Persist to ``CONFIG_PATH`` and invalidate the cache."""
    local_storage.mkdir(CONFIG_DIR)
    with local_storage.open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(
            cfg.model_dump(mode="json", by_alias=True),
            f,
            default_flow_style=False,
            allow_unicode=True,
        )
    reload_config()


def get_config() -> CliConfig:
    """Return the cached config (loads from disk on first call)."""
    global _cached
    if _cached is None:
        with _cache_lock:
            if _cached is None:
                _cached = load_cli_config()
    return _cached


def reload_config() -> CliConfig:
    """Drop the cache so the next ``get_config()`` re-reads from disk."""
    global _cached
    with _cache_lock:
        _cached = None
    return get_config()


# ── Database registry helpers ───────────────────────────────────────────────


def get_active_db() -> str | None:
    cfg = load_cli_config()
    active = cfg.active_database
    return active.path if active else None


def add_database(db_path: str | Path, name: str | None = None) -> int:
    cfg = load_cli_config()
    target = DatabaseTarget.from_value(db_path)
    for i, entry in enumerate(cfg.databases):
        if DatabaseTarget.from_value(entry.path).identity == target.identity:
            return i
    cfg.databases.append(RegisteredDatabase(path=target.display, name=name or ""))
    if len(cfg.databases) == 1:
        cfg.active = 0
    save_cli_config(cfg)
    return len(cfg.databases) - 1


def set_active_database(index: int) -> str:
    cfg = load_cli_config()
    if index < 0 or index >= len(cfg.databases):
        raise ValueError(f"Invalid index {index + 1}. Have {len(cfg.databases)} database(s).")
    cfg.active = index
    save_cli_config(cfg)
    return cfg.databases[index].path


def remove_database(index: int) -> str:
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
