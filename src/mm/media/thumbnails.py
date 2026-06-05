"""Thumbnail generation with disk cache."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from mm.config import VIDEO_EXTENSIONS, get_config
from mm.io import FileStorage

_FFMPEG: str | None = shutil.which("ffmpeg")


def cache_dir_for_library(library_id: str | None, base: Path | None = None) -> Path:
    """Return ``base/<library_id>``; falls back to ``base`` when id is empty."""
    base = base or get_config().paths.thumbs_dir
    return base / library_id if library_id else base


def get_thumbnail(
    source_path: str,
    media_id: int,
    size: str = "md",
    cache_dir: Path | None = None,
    *,
    storage: FileStorage,
) -> Path | None:
    """Return path to a cached thumbnail, generating if needed."""
    cfg = get_config().thumbnails
    cache_dir = cache_dir or get_config().paths.thumbs_dir
    if size not in cfg.sizes:
        size = "md"

    dest = cache_dir / size / f"{media_id}.webp"

    if storage.exists(dest):
        try:
            if storage.get_mtime(source_path) <= storage.get_mtime(dest):
                return dest
        except OSError:
            pass

    ext = Path(source_path).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return _generate_video(source_path, dest, cfg.sizes[size], storage=storage)
    return _generate_image(source_path, dest, cfg.sizes[size], storage=storage)


def clear_cache(
    cache_dir: Path | None = None,
    *,
    storage: FileStorage,
) -> int:
    """Remove all cached thumbnails. Returns count deleted."""
    cache_dir = cache_dir or get_config().paths.thumbs_dir
    count = 0
    if storage.exists(cache_dir):
        for path in storage.rglob_files(cache_dir):
            storage.delete_file(path)
            count += 1
    return count


def _generate_image(
    source_path: str,
    dest: Path,
    max_size: tuple[int, int],
    *,
    storage: FileStorage,
) -> Path | None:
    _try_register_heif()
    img = None

    # Prefer rawpy for camera raw formats (better quality than Pillow fallback).
    lower_ext = Path(source_path).suffix.lower()
    if lower_ext in (".cr2", ".nef", ".arw", ".dng", ".raf", ".orf"):
        try:
            import rawpy

            with rawpy.imread(source_path) as raw:
                try:
                    thumb = raw.extract_thumb()
                except rawpy.LibRawNoThumbnailError:
                    thumb = None

                if thumb and thumb.format == rawpy.ThumbFormat.JPEG:
                    import io

                    img = Image.open(io.BytesIO(thumb.data))
                else:
                    rgb = raw.postprocess(use_camera_wb=True)
                    img = Image.fromarray(rgb)
        except (ImportError, Exception):
            pass

    if img is None:
        try:
            with storage.open(source_path, "rb") as f:
                img = Image.open(f)
                img.load()
        except Exception:
            return None

    try:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")

        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        storage.mkdir(dest.parent)

        fd, tmp_path = tempfile.mkstemp(suffix=".webp", dir=dest.parent)
        os.close(fd)

        img.save(tmp_path, "WEBP", quality=80, method=4)
        storage.replace(tmp_path, dest)

        return dest
    except Exception:
        if "tmp_path" in locals() and storage.exists(tmp_path):
            storage.delete_file(tmp_path)
        return None
    finally:
        if img:
            img.close()


def _generate_video(
    source_path: str,
    dest: Path,
    max_size: tuple[int, int],
    *,
    storage: FileStorage,
) -> Path | None:
    """Extract a frame via ffmpeg (1s seek, fall back to first frame)."""
    if _FFMPEG is None:
        return None

    storage.mkdir(dest.parent)

    fd, tmp_png = tempfile.mkstemp(suffix=".png", dir=dest.parent)
    os.close(fd)

    try:
        extracted = False
        for seek_args in [["-ss", "1"], ["-ss", "0"]]:
            result = subprocess.run(
                [
                    _FFMPEG,
                    *seek_args,
                    "-i",
                    source_path,
                    "-frames:v",
                    "1",
                    "-an",
                    "-y",
                    "-threads",
                    "1",
                    "-loglevel",
                    "error",
                    tmp_png,
                ],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0 and storage.get_size(tmp_png) > 0:
                extracted = True
                break
        if not extracted:
            return None

        try:
            img = Image.open(tmp_png)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            _write_atomic(img, dest, storage=storage)
            img.close()
            return dest
        except Exception:
            return None
    except (subprocess.TimeoutExpired, Exception):
        return None
    finally:
        try:
            storage.delete_file(tmp_png)
        except OSError:
            pass


def _write_atomic(
    img: Image.Image,
    dest: Path,
    *,
    storage: FileStorage,
) -> None:
    storage.mkdir(dest.parent)
    fd, tmp = tempfile.mkstemp(suffix=".webp", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            img.save(f, format="WEBP", quality=80, method=4)
        storage.replace(tmp, dest)
    except Exception:
        try:
            storage.delete_file(tmp)
        except OSError:
            pass
        raise


_heif_registered = False


def _try_register_heif() -> None:
    global _heif_registered
    if _heif_registered:
        return
    _heif_registered = True
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
