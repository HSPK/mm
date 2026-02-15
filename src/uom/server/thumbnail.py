"""Thumbnail generation with disk cache.

Strategy:
- Photo thumbnails: Pillow (LANCZOS) → WebP with disk cache.
- Video thumbnails: ffmpeg frame extraction → Pillow resize → WebP.
- Cache keyed by media_id + size, invalidated when source mtime changes.
- Concurrent-safe via atomic write (tempfile + os.replace).
- HEIC/HEIF support via pillow-heif plugin.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from uom.config import VIDEO_EXTENSIONS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUMB_SIZES = {
    "sm": (200, 200),
    "md": (400, 400),
    "lg": (800, 800),
    "xl": (1920, 1080),  # Full HD preview
}

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "uom" / "thumbs"

_FFMPEG: str | None = shutil.which("ffmpeg")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_thumbnail(
    source_path: str,
    media_id: int,
    size: str = "md",
    cache_dir: Path | None = None,
) -> Path | None:
    """Return path to a cached thumbnail, generating if needed.

    Returns None if the source can't be decoded or doesn't exist.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    if size not in THUMB_SIZES:
        size = "md"

    dest = _cache_path(cache_dir, media_id, size)

    # Fast path: already cached and not stale
    if dest.exists():
        try:
            if os.path.getmtime(source_path) <= dest.stat().st_mtime:
                return dest
        except OSError:
            pass

    ext = Path(source_path).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return _generate_video(source_path, dest, THUMB_SIZES[size])
    return _generate_image(source_path, dest, THUMB_SIZES[size])


def clear_cache(cache_dir: Path | None = None) -> int:
    """Remove all cached thumbnails. Returns count deleted."""
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    count = 0
    if cache_dir.exists():
        for f in cache_dir.rglob("*"):
            if f.is_file():
                f.unlink()
                count += 1
    return count


# ---------------------------------------------------------------------------
# Cache path
# ---------------------------------------------------------------------------


def _cache_path(cache_dir: Path, media_id: int, size: str, ext: str = ".webp") -> Path:
    """Deterministic cache path for a thumbnail."""
    return cache_dir / size / f"{media_id}{ext}"


# ---------------------------------------------------------------------------
# Image thumbnail
# ---------------------------------------------------------------------------


def _generate_image(source_path: str, dest: Path, max_size: tuple[int, int]) -> Path | None:
    """Generate a thumbnail from an image file."""
    _try_register_heif()
    img = None

    # Try rawpy for raw files first as it produces better results/compatibility
    lower_ext = Path(source_path).suffix.lower()
    if lower_ext in (".cr2", ".nef", ".arw", ".dng", ".raf", ".orf"):
        try:
            import rawpy

            with rawpy.imread(source_path) as raw:
                # Use embedded preview if available for speed, otherwise postprocess
                try:
                    thumb = raw.extract_thumb()
                except rawpy.LibRawNoThumbnailError:
                    thumb = None

                if thumb and thumb.format == rawpy.ThumbFormat.JPEG:
                    # Load JPEG bytes into Pillow
                    import io

                    img = Image.open(io.BytesIO(thumb.data))
                else:
                    # Fallback to full conversion (slower but high quality)
                    rgb = raw.postprocess(use_camera_wb=True)
                    img = Image.fromarray(rgb)
        except (ImportError, Exception):
            pass  # Fallback to Pillow

    if img is None:
        try:
            img = Image.open(source_path)
            # Handle HEIF/AVIF specifically via pillow_heif if needed,
            # but Image.open usually handles it if registered.
        except Exception:
            return None

    try:
        img = ImageOps.exif_transpose(img)
        # Ensure we have a compatible mode for WebP (RGB, RGBA)
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")

        # Resize maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Ensure destination directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file then move (atomic)
        fd, tmp_path = tempfile.mkstemp(suffix=".webp", dir=dest.parent)
        os.close(fd)

        # Save as optimized WebP
        img.save(tmp_path, "WEBP", quality=80, method=4)
        os.replace(tmp_path, dest)

        return dest
    except Exception:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None
    finally:
        if img:
            img.close()


# ---------------------------------------------------------------------------
# Video thumbnail (via ffmpeg)
# ---------------------------------------------------------------------------


def _generate_video(source_path: str, dest: Path, max_size: tuple[int, int]) -> Path | None:
    """Extract a frame from a video and generate a thumbnail.

    Tries to grab a frame at 1 second; if that fails, tries the first frame.
    """
    if _FFMPEG is None:
        return None

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Extract frame to a temp PNG
    fd, tmp_png = tempfile.mkstemp(suffix=".png", dir=dest.parent)
    os.close(fd)

    try:
        # Try at 1 second mark first (better representative frame)
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
                    "-loglevel",
                    "error",
                    tmp_png,
                ],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0 and os.path.getsize(tmp_png) > 0:
                extracted = True
                break
        if not extracted:
            return None

        # Resize with Pillow
        try:
            img = Image.open(tmp_png)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            _write_atomic(img, dest)
            img.close()
            return dest
        except Exception:
            return None
    except (subprocess.TimeoutExpired, Exception):
        return None
    finally:
        try:
            os.unlink(tmp_png)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _write_atomic(img: Image.Image, dest: Path) -> None:
    """Write an image to *dest* atomically via temp + rename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".webp", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            img.save(f, format="WEBP", quality=80, method=4)
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# HEIF registration
# ---------------------------------------------------------------------------

_heif_registered = False


def _try_register_heif() -> None:
    """Register pillow-heif if available (called once)."""
    global _heif_registered
    if _heif_registered:
        return
    _heif_registered = True
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
