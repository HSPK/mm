from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from mm.config import ALL_MEDIA_EXTENSIONS
from mm.db.dto import User
from mm.server.dependencies import get_current_user
from mm.server.utility_schemas import FileBrowserEntry, FileBrowserResponse

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/browse", response_model=FileBrowserResponse)
async def browse_files(
    path: str | None = Query(default=None),
    select: str = Query(default="any", pattern="^(any|file|directory|media)$"),
    show_hidden: bool = False,
    _u: User | None = Depends(get_current_user),
) -> FileBrowserResponse:
    current = _resolve_browser_path(path)
    if current.is_file():
        current = current.parent

    entries: list[FileBrowserEntry] = []
    try:
        children = sorted(
            current.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
    except OSError:
        children = []

    for child in children:
        if not show_hidden and child.name.startswith("."):
            continue
        try:
            stat = child.stat()
            is_dir = child.is_dir()
            is_file = child.is_file()
        except OSError:
            continue
        entries.append(
            FileBrowserEntry(
                name=child.name,
                path=str(child),
                is_dir=is_dir,
                is_file=is_file,
                extension=child.suffix.lower() if is_file else "",
                size=stat.st_size if is_file else None,
                modified_at=stat.st_mtime,
                selectable=_is_selectable(child, select),
            )
        )

    return FileBrowserResponse(
        path=str(current),
        parent=str(current.parent) if current.parent != current else None,
        roots=_browser_roots(),
        entries=entries,
    )


def _resolve_browser_path(path: str | None) -> Path:
    if path and path.strip():
        return Path(path).expanduser().resolve()
    return Path.home().resolve()


def _browser_roots() -> list[str]:
    roots = [str(Path.home().resolve()), str(Path.cwd().resolve())]
    root = Path("/").resolve()
    if str(root) not in roots:
        roots.append(str(root))
    return roots


def _is_selectable(path: Path, select: str) -> bool:
    if select == "any":
        return path.is_dir() or path.is_file()
    if select == "directory":
        return path.is_dir()
    if select == "file":
        return path.is_file()
    if select == "media":
        return path.is_dir() or path.suffix.lower() in ALL_MEDIA_EXTENSIONS
    return False
