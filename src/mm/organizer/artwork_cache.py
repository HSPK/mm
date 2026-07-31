"""Artwork discovery and thumbnail cache for organizer media."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from mm.config import get_config
from mm.music.grouping import music_album_directory, music_album_disc_directories

ARTWORK_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def artwork_directories(path: Path, media_type: str) -> list[Path]:
    directories = [path.parent]
    if media_type == "track":
        album_directory = music_album_directory(path)
        if album_directory != path.parent:
            directories.append(album_directory)
            directories.extend(music_album_disc_directories(path))
    if media_type == "tv":
        directories.append(path.parent.parent)
    return directories


def first_artwork_path(path: Path, media_type: str) -> Path | None:
    for directory in artwork_directories(path, media_type):
        files = artwork_files(directory)
        if files:
            return files[0]
    return None


def artwork_path_by_kind(path: Path, media_type: str, kind: str) -> Path | None:
    """Return the first artwork of a specific kind (poster/fanart/clearlogo)."""
    for directory in artwork_directories(path, media_type):
        for candidate in artwork_files(directory):
            if artwork_kind(candidate) == kind:
                return candidate
    return None


def artwork_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = [
        child
        for child in sorted(directory.iterdir(), key=lambda item: item.name.lower())
        if child.is_file()
        and not child.name.startswith("._")
        and child.suffix.lower() in ARTWORK_EXTENSIONS
        and artwork_kind(child)
    ]
    return sorted(files, key=lambda item: (_artwork_priority(item), item.name.lower()))


def artwork_kind(path: Path) -> str:
    stem = path.stem.lower()
    if stem in {"cd", "folder", "cover", "poster"}:
        return "poster"
    if stem in {"fanart", "backdrop", "background"}:
        return "fanart"
    if stem in {"clearlogo", "logo"}:
        return "clearlogo"
    if "poster" in stem or "cover" in stem or "folder" in stem:
        return "poster"
    if "fanart" in stem or "backdrop" in stem:
        return "fanart"
    if "logo" in stem:
        return "clearlogo"
    return ""


def _artwork_priority(path: Path) -> int:
    return {
        "poster": 0,
        "fanart": 1,
        "clearlogo": 2,
    }.get(artwork_kind(path), 9)


def artwork_thumbnail(path: Path, size: int) -> Path | None:
    size = _safe_size(size)
    if not path.is_file() or path.suffix.lower() not in ARTWORK_EXTENSIONS:
        return None
    dest = _thumbnail_path(path, size)
    try:
        if dest.exists() and path.stat().st_mtime_ns <= dest.stat().st_mtime_ns:
            return dest
    except OSError:
        return None
    return _generate_thumbnail(path, dest, size)


def _safe_size(size: int) -> int:
    if size <= 0:
        return 320
    return max(96, min(size, 1024))


def _thumbnail_path(path: Path, size: int) -> Path:
    stat = path.stat()
    key = hashlib.sha256(
        f"{path.expanduser().resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{size}".encode()
    ).hexdigest()
    return get_config().paths.cache_dir / "organizer-artwork" / str(size) / f"{key}.webp"


def _generate_thumbnail(path: Path, dest: Path, size: int) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".webp", dir=dest.parent)
    os.close(fd)
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "RGBA", "L"}:
                image = image.convert("RGB")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            image.save(tmp_path, "WEBP", quality=82, method=4)
        Path(tmp_path).replace(dest)
        return dest
    except OSError:
        Path(tmp_path).unlink(missing_ok=True)
        return None
