from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from mm.config import load_cli_config


class AuthorizedMediaPath:
    """A resolved path which is contained by one configured organizer source."""

    def __init__(self, path: Path, root: Path) -> None:
        self.path = path
        self.root = root

    @classmethod
    def resolve(
        cls,
        value: str | Path,
        *,
        must_exist: bool = False,
        file: bool = False,
        detail: str = "Path is outside configured media sources",
    ) -> AuthorizedMediaPath:
        path = Path(value).expanduser().resolve()
        roots = configured_media_roots()
        root = next(
            (
                candidate
                for candidate in sorted(roots, key=lambda item: len(item.parts), reverse=True)
                if is_relative_to(path, candidate)
            ),
            None,
        )
        if root is None:
            raise HTTPException(403, detail)
        if must_exist and not path.exists():
            raise HTTPException(404, "Media path not found")
        if file and not path.is_file():
            raise HTTPException(400, "Path is not a file")
        return cls(path, root)

    def output(self, value: str | Path) -> Path:
        """Authorize a sidecar/output path under this path's configured root."""
        target = Path(value).expanduser().resolve()
        if not is_relative_to(target, self.root):
            raise HTTPException(403, "Output path is outside configured media sources")
        return target


def configured_media_roots() -> list[Path]:
    cfg = load_cli_config()
    return [
        Path(source).expanduser().resolve()
        for sources in cfg.organizer.media_sources.values()
        for source in sources
    ]


def authorized_media_path(
    value: str | Path, *, must_exist: bool = False, file: bool = False
) -> AuthorizedMediaPath:
    return AuthorizedMediaPath.resolve(value, must_exist=must_exist, file=file)


def allowed_media_source_path(path: Path) -> bool:
    try:
        AuthorizedMediaPath.resolve(path)
    except HTTPException:
        return False
    return True


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
