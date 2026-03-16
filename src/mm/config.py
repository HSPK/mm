from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

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
DEFAULT_IMPORT_TEMPLATE = "{year}/{year}-{month:02d}-{day:02d}/{original_name}{ext}"
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"
CLIP_CONFIDENCE_THRESHOLD = 0.25
HASH_CHUNK_SIZE = 8192


def resolve_media_path(stored_path: str, library_root: str | Path) -> str:
    """Resolve a stored (possibly relative) media path to an absolute path.

    Backward-compatible: if *stored_path* is already absolute it is returned
    as-is.
    """
    if os.path.isabs(stored_path):
        return stored_path
    return os.path.normpath(os.path.join(str(library_root), stored_path))


def make_relative_path(abs_path: str, library_root: str | Path) -> str:
    """Convert an absolute path to one relative to *library_root*."""
    return os.path.relpath(abs_path, str(library_root))


# ---------------------------------------------------------------------------
# User config file (~/.config/mm.yaml)
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config"
CONFIG_PATH = CONFIG_DIR / "mm.yaml"


def _default_config() -> dict[str, Any]:
    return {"databases": [], "active": -1}


def load_config() -> dict[str, Any]:
    """Load the user config from ~/.config/mm.yaml."""
    if not CONFIG_PATH.exists():
        return _default_config()
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return _default_config()
    data.setdefault("databases", [])
    data.setdefault("active", -1)
    return data


def save_config(cfg: dict[str, Any]) -> None:
    """Write the user config to ~/.config/mm.yaml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)


def get_active_db() -> Path | None:
    """Return the path of the currently active database, or None."""
    cfg = load_config()
    idx = cfg.get("active", -1)
    dbs = cfg.get("databases", [])
    if not dbs or idx < 0 or idx >= len(dbs):
        return None
    return Path(dbs[idx]["path"])


def add_database(db_path: Path, name: str | None = None) -> int:
    """Add a database to the config.  Returns its index."""
    cfg = load_config()
    abs_path = str(db_path.resolve())
    # Avoid duplicates
    for i, entry in enumerate(cfg["databases"]):
        if str(Path(entry["path"]).resolve()) == abs_path:
            return i
    entry: dict[str, str] = {"path": abs_path}
    if name:
        entry["name"] = name
    cfg["databases"].append(entry)
    # If this is the first DB, auto-activate it
    if len(cfg["databases"]) == 1:
        cfg["active"] = 0
    save_config(cfg)
    return len(cfg["databases"]) - 1


def set_active_database(index: int) -> Path:
    """Set the active database by index (1-based from user, 0-based internal).

    Raises ValueError if the index is out of range.
    """
    cfg = load_config()
    dbs = cfg.get("databases", [])
    if index < 0 or index >= len(dbs):
        raise ValueError(f"Invalid index {index + 1}. Have {len(dbs)} database(s).")
    cfg["active"] = index
    save_config(cfg)
    return Path(dbs[index]["path"])


def remove_database(index: int) -> Path:
    """Remove a database from the config by 0-based index.

    Adjusts the active index accordingly.  Raises ValueError if out of range.
    Returns the path that was removed.
    """
    cfg = load_config()
    dbs = cfg.get("databases", [])
    if index < 0 or index >= len(dbs):
        raise ValueError(f"Invalid index {index + 1}. Have {len(dbs)} database(s).")
    removed = Path(dbs.pop(index)["path"])
    active = cfg.get("active", -1)
    if active == index:
        cfg["active"] = 0 if dbs else -1
    elif active > index:
        cfg["active"] = active - 1
    save_config(cfg)
    return removed
