from __future__ import annotations

from pathlib import Path

from mm.organizer.filename import _disc_from_folder


def music_album_key_from_path(path: Path) -> str:
    return f"music:{music_album_directory(path).expanduser()}"


def music_album_directory(path: Path) -> Path:
    directory = path.parent
    if disc_from_path_directory(directory.name) is not None:
        directory = directory.parent
    return directory


def music_album_disc_directories(path: Path) -> list[Path]:
    album_directory = music_album_directory(path)
    if album_directory == path.parent:
        return []
    try:
        children = list(album_directory.iterdir())
    except OSError:
        return []
    return sorted(
        (
            child
            for child in children
            if child != path.parent
            and child.is_dir()
            and disc_from_path_directory(child.name) is not None
        ),
        key=lambda child: child.name.casefold(),
    )


def disc_from_path_directory(name: str) -> int | None:
    return _disc_from_folder(name)
