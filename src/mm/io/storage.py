"""File storage abstraction.

The default implementation wraps the local filesystem.  Callers should depend on
``FileStorage`` methods instead of directly using ``Path``/``os``/``shutil`` so
other storage backends can be added later.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO, Protocol, TextIO, overload


class FileStorage(Protocol):
    def resolve(self, path: str | Path) -> Path: ...

    def exists(self, path: str | Path) -> bool: ...

    def is_file(self, path: str | Path) -> bool: ...

    def is_dir(self, path: str | Path) -> bool: ...

    def stat(self, path: str | Path) -> os.stat_result: ...

    def get_size(self, path: str | Path) -> int: ...

    def get_mtime(self, path: str | Path) -> float: ...

    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None: ...

    @overload
    def open(self, path: str | Path, mode: str = "rb", **kwargs: Any) -> BinaryIO: ...

    @overload
    def open(self, path: str | Path, mode: str = "r", **kwargs: Any) -> TextIO: ...

    def open(self, path: str | Path, mode: str = "rb", **kwargs: Any) -> BinaryIO | TextIO: ...

    def read_bytes(self, path: str | Path) -> bytes: ...

    def write_bytes(self, path: str | Path, data: bytes) -> None: ...

    def copy(self, source: str | Path, destination: str | Path) -> None: ...

    def move(self, source: str | Path, destination: str | Path) -> None: ...

    def replace(self, source: str | Path, destination: str | Path) -> None: ...

    def delete_file(self, path: str | Path, *, missing_ok: bool = False) -> None: ...

    def iter_files(
        self,
        directory: str | Path,
        *,
        allowed_extensions: frozenset[str] | set[str] | None = None,
        skip_hidden: bool = True,
    ) -> Iterator[Path]: ...

    def rglob_files(self, directory: str | Path) -> Iterator[Path]: ...


class LocalStorage:
    """Local filesystem-backed storage."""

    def resolve(self, path: str | Path) -> Path:
        return Path(path).resolve()

    def exists(self, path: str | Path) -> bool:
        return Path(path).exists()

    def is_file(self, path: str | Path) -> bool:
        return Path(path).is_file()

    def is_dir(self, path: str | Path) -> bool:
        return Path(path).is_dir()

    def stat(self, path: str | Path) -> os.stat_result:
        return Path(path).stat()

    def get_size(self, path: str | Path) -> int:
        return self.stat(path).st_size

    def get_mtime(self, path: str | Path) -> float:
        return self.stat(path).st_mtime

    def mkdir(self, path: str | Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def open(self, path: str | Path, mode: str = "rb", **kwargs: Any) -> BinaryIO | TextIO:
        return Path(path).open(mode, **kwargs)

    def read_bytes(self, path: str | Path) -> bytes:
        return Path(path).read_bytes()

    def write_bytes(self, path: str | Path, data: bytes) -> None:
        Path(path).write_bytes(data)

    def copy(self, source: str | Path, destination: str | Path) -> None:
        shutil.copy2(str(source), str(destination))

    def move(self, source: str | Path, destination: str | Path) -> None:
        shutil.move(str(source), str(destination))

    def replace(self, source: str | Path, destination: str | Path) -> None:
        os.replace(source, destination)

    def delete_file(self, path: str | Path, *, missing_ok: bool = False) -> None:
        Path(path).unlink(missing_ok=missing_ok)

    def iter_files(
        self,
        directory: str | Path,
        *,
        allowed_extensions: frozenset[str] | set[str] | None = None,
        skip_hidden: bool = True,
    ) -> Iterator[Path]:
        for root, dirs, files in os.walk(directory):
            if skip_hidden:
                dirs[:] = [name for name in dirs if not name.startswith(".")]
            for name in files:
                if skip_hidden and name.startswith("."):
                    continue
                path = Path(root) / name
                if allowed_extensions is None or path.suffix.lower() in allowed_extensions:
                    yield path

    def rglob_files(self, directory: str | Path) -> Iterator[Path]:
        root = Path(directory)
        if not root.exists():
            return
        for path in root.rglob("*"):
            if path.is_file():
                yield path


local_storage: FileStorage = LocalStorage()
