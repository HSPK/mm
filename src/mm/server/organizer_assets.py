from __future__ import annotations

from pathlib import Path

from PIL import Image

from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from mm.music.grouping import music_album_directory, music_album_disc_directories
from mm.server.organizer_metadata import OrganizerScanContext, normalized_path_key
from mm.server.organizer_schemas import OrganizerArtworkAsset, OrganizerFileAsset

_SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub", ".idx"}
_LYRICS_EXTENSIONS = {".lrc"}
_SUBTITLE_DIRECTORIES = {"subs", "subtitles", "subtitle"}


def _artwork_assets(
    path: Path,
    media_type: str,
    context: OrganizerScanContext | None = None,
) -> list[OrganizerArtworkAsset]:
    assets: list[OrganizerArtworkAsset] = []
    seen: set[Path] = set()
    for directory in _artwork_directories(path, media_type):
        for child in _artwork_files(directory, context):
            kind = _artwork_kind(child)
            if not kind:
                continue
            resolved = normalized_path_key(child)
            if resolved in seen:
                continue
            seen.add(resolved)
            width, height = _image_size(child, context)
            assets.append(
                OrganizerArtworkAsset(
                    kind=kind,
                    path=str(child),
                    label=child.name,
                    width=width,
                    height=height,
                )
            )
    return assets


def _has_artwork(
    path: Path,
    media_type: str,
    context: OrganizerScanContext | None = None,
) -> bool:
    return any(
        _artwork_files(directory, context) for directory in _artwork_directories(path, media_type)
    )


def _artwork_directories(path: Path, media_type: str) -> list[Path]:
    directories = [path.parent]
    if media_type == "track":
        album_directory = music_album_directory(path)
        if album_directory != path.parent:
            directories.append(album_directory)
            directories.extend(music_album_disc_directories(path))
    if media_type == "tv":
        directories.append(path.parent.parent)
    return directories


def _directory_children(
    directory: Path,
    context: OrganizerScanContext | None = None,
) -> list[Path]:
    if context:
        return context.list_children(directory)
    if not directory.is_dir():
        return []
    return sorted(
        (child for child in directory.iterdir() if not child.name.startswith("._")),
        key=lambda item: item.name.lower(),
    )


def _artwork_files(
    directory: Path,
    context: OrganizerScanContext | None = None,
) -> list[Path]:
    key = normalized_path_key(directory)
    if context and key in context.artwork_files:
        return context.artwork_files[key]
    files = [
        child
        for child in _directory_children(directory, context)
        if child.is_file()
        and not child.name.startswith("._")
        and child.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        and _artwork_kind(child)
    ]
    if context:
        context.artwork_files[key] = files
    return files


def _related_files(
    path: Path,
    media_type: str,
    context: OrganizerScanContext | None = None,
) -> list[OrganizerFileAsset]:
    if media_type == "track":
        return _track_related_files(path, context)
    files: list[OrganizerFileAsset] = []
    seen: set[Path] = set()
    for directory in _artwork_directories(path, media_type):
        children = _directory_children(directory, context)
        for child in children:
            if not child.is_file() or child.name.startswith("._"):
                continue
            resolved = normalized_path_key(child)
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(
                OrganizerFileAsset(
                    kind=_file_kind(child),
                    path=str(child),
                    name=child.name,
                    extension=child.suffix.lower(),
                    size=child.stat().st_size,
                )
            )
    return files


def _track_related_files(
    path: Path,
    context: OrganizerScanContext | None = None,
) -> list[OrganizerFileAsset]:
    files: list[OrganizerFileAsset] = []
    candidates = [
        path,
        path.with_suffix(".nfo"),
        path.with_suffix(".lrc"),
        path.with_name(f"{path.stem}.lyrics.txt"),
        path.with_name(f"{path.stem}.lyric.txt"),
        music_album_directory(path) / "album.nfo",
    ]
    for directory in _artwork_directories(path, "track"):
        candidates.extend(_artwork_files(directory, context))
    seen: set[Path] = set()
    for child in candidates:
        if not child.is_file() or child.name.startswith("._"):
            continue
        resolved = normalized_path_key(child)
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(
            OrganizerFileAsset(
                kind=_file_kind(child),
                path=str(child),
                name=child.name,
                extension=child.suffix.lower(),
                size=child.stat().st_size,
            )
        )
    return files


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix == ".nfo":
        return "metadata"
    if suffix in _SUBTITLE_EXTENSIONS:
        return "subtitle"
    if suffix in _LYRICS_EXTENSIONS or _is_text_lyrics(path):
        return "lyrics"
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return _artwork_kind(path) or "image"
    return suffix.lstrip(".") or "file"


def _artwork_kind(path: Path) -> str:
    stem = path.stem.lower()
    for kind in (
        "cd",
        "poster",
        "fanart",
        "banner",
        "clearlogo",
        "clearart",
        "landscape",
        "folder",
        "cover",
    ):
        if stem == kind or stem.endswith(f"-{kind}") or stem.endswith(f".{kind}"):
            return "poster" if kind in {"cd", "folder", "cover"} else kind
    return ""


def _image_size(
    path: Path,
    context: OrganizerScanContext | None = None,
) -> tuple[int | None, int | None]:
    key = normalized_path_key(path)
    if context and key in context.image_sizes:
        return context.image_sizes[key]
    try:
        with Image.open(path) as image:
            size = image.size
    except OSError:
        size = (None, None)
    if context:
        context.image_sizes[key] = size
    return size


def _has_subtitles(path: Path, context: OrganizerScanContext | None = None) -> bool:
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        return False
    parent = path.parent
    single_video = _single_video_directory(parent, context)
    if _subtitle_in_directory(path, parent, context, allow_any=single_video):
        return True
    for child in _directory_children(parent, context):
        if child.is_dir() and child.name.lower() in _SUBTITLE_DIRECTORIES:
            if _subtitle_in_directory(
                path,
                child,
                context,
                allow_any=single_video,
            ):
                return True
    return False


def _subtitle_in_directory(
    video_path: Path,
    directory: Path,
    context: OrganizerScanContext | None = None,
    *,
    allow_any: bool = False,
) -> bool:
    for candidate in _directory_children(directory, context):
        if not candidate.is_file() or candidate.suffix.lower() not in _SUBTITLE_EXTENSIONS:
            continue
        if allow_any or candidate.stem.startswith(video_path.stem):
            return True
    return False


def _single_video_directory(directory: Path, context: OrganizerScanContext | None = None) -> bool:
    return (
        sum(
            1
            for candidate in _directory_children(directory, context)
            if candidate.is_file() and candidate.suffix.lower() in VIDEO_EXTENSIONS
        )
        <= 1
    )


def _has_lyrics(path: Path, context: OrganizerScanContext | None = None) -> bool:
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        return False
    return any(candidate.is_file() for candidate in _lyric_sidecar_paths(path))


def _is_text_lyrics(path: Path) -> bool:
    return path.suffix.lower() == ".txt" and path.stem.lower().endswith(("lyrics", "lyric"))


def _sidecar_lyrics(
    path: Path,
    context: OrganizerScanContext | None = None,
) -> tuple[str | None, str | None]:
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        return None, None
    lrc = path.with_suffix(".lrc")
    if lrc.exists():
        return None, _read_text_file(lrc)
    for candidate in _lyric_sidecar_paths(path):
        if _is_text_lyrics(candidate):
            return _read_text_file(candidate), None
    return None, None


def _lyric_sidecar_paths(path: Path) -> list[Path]:
    return [
        path.with_suffix(".lrc"),
        path.with_name(f"{path.stem}.lyrics.txt"),
        path.with_name(f"{path.stem}.lyric.txt"),
    ]


def _read_text_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
