"""Safe dry-run/apply rename planning."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mm.config import OrganizerTemplates
from mm.organizer.filename import ParsedMediaFile
from mm.organizer.templates import render_media_path


@dataclass(frozen=True)
class RenameOperation:
    source: Path
    target: Path
    media_type: str
    status: str
    reason: str = ""

    @property
    def changed(self) -> bool:
        return self.source.resolve() != self.target.resolve()


@dataclass(frozen=True)
class RenamePlan:
    root: Path
    operations: list[RenameOperation]

    @property
    def actionable(self) -> list[RenameOperation]:
        return [op for op in self.operations if op.status == "ready"]

    @property
    def conflicts(self) -> list[RenameOperation]:
        return [op for op in self.operations if op.status == "conflict"]


def plan_renames(
    items: list[ParsedMediaFile],
    *,
    root: Path,
    templates: OrganizerTemplates,
) -> RenamePlan:
    root = root.expanduser().resolve()
    return _build_plan(
        items,
        root_for_item=lambda _item: root,
        display_root=root,
        templates=templates,
    )


def plan_renames_with_source_roots(
    items: list[ParsedMediaFile],
    *,
    roots: list[Path],
    templates: OrganizerTemplates,
) -> RenamePlan:
    resolved_roots = [root.expanduser().resolve() for root in roots]

    return _build_plan(
        items,
        root_for_item=lambda item: _source_root_for_item(item, resolved_roots),
        display_root=resolved_roots[0] if resolved_roots else Path.cwd(),
        templates=templates,
    )


def _build_plan(
    items: list[ParsedMediaFile],
    *,
    root_for_item: Callable[[ParsedMediaFile], Path],
    display_root: Path,
    templates: OrganizerTemplates,
) -> RenamePlan:
    seen_targets: dict[Path, Path] = {}
    seen_sources: set[Path] = set()
    operations: list[RenameOperation] = []

    for item in items:
        root = root_for_item(item)
        rendered = render_media_path(item, templates)
        primary_target = (root / rendered.relative_path).resolve()
        operations.extend(
            _planned_operations_for_item(
                item,
                primary_target,
                seen_targets,
                seen_sources,
            )
        )

    return RenamePlan(root=display_root.expanduser().resolve(), operations=operations)


def _source_root_for_item(item: ParsedMediaFile, roots: list[Path]) -> Path:
    source = item.path.expanduser().resolve()
    matches = [root for root in roots if _is_relative_to(source, root)]
    if not matches:
        return source.parent
    return max(matches, key=lambda root: len(root.parts))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _planned_operations_for_item(
    item: ParsedMediaFile,
    primary_target: Path,
    seen_targets: dict[Path, Path],
    seen_sources: set[Path],
) -> list[RenameOperation]:
    operations: list[RenameOperation] = []
    sources = [item.path.expanduser().resolve(), *_sidecar_files(item)]
    for source in sources:
        if source in seen_sources:
            continue
        seen_sources.add(source)
        target = _target_for_source(item, primary_target, source)
        status = "ready"
        reason = ""
        if source == target:
            status = "unchanged"
        elif target in seen_targets and seen_targets[target] != source:
            status = "conflict"
            reason = f"duplicate target also used by {seen_targets[target]}"
        elif target.exists():
            status = "conflict"
            reason = "target exists"
        seen_targets[target] = source
        operations.append(RenameOperation(source, target, item.media_type, status, reason))
    return operations


def _sidecar_files(item: ParsedMediaFile) -> list[Path]:
    source = item.path.expanduser().resolve()
    candidates: list[Path] = []
    candidates.extend(_same_stem_sidecars(source))
    candidates.extend(_standard_artwork_sidecars(source.parent))
    if item.media_type == "tv":
        candidates.extend(_standard_artwork_sidecars(source.parent.parent))
    return _dedupe_existing(candidates, source)


def _same_stem_sidecars(source: Path) -> list[Path]:
    return [
        candidate.resolve()
        for candidate in source.parent.glob(f"{source.stem}*")
        if candidate.is_file()
        and candidate.resolve() != source
        and not candidate.name.startswith("._")
    ]


def _standard_artwork_sidecars(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    names = {
        "movie.nfo",
        "tvshow.nfo",
        "album.nfo",
        "poster.jpg",
        "poster.jpeg",
        "poster.png",
        "poster.webp",
        "fanart.jpg",
        "fanart.jpeg",
        "fanart.png",
        "fanart.webp",
        "folder.jpg",
        "folder.jpeg",
        "folder.png",
        "folder.webp",
        "cover.jpg",
        "cover.jpeg",
        "cover.png",
        "cover.webp",
        "banner.jpg",
        "banner.jpeg",
        "banner.png",
        "banner.webp",
        "clearlogo.png",
        "clearlogo.webp",
    }
    return [
        candidate.resolve()
        for candidate in directory.iterdir()
        if candidate.is_file()
        and not candidate.name.startswith("._")
        and (
            candidate.name.lower() in names
            or candidate.stem.lower().startswith("season")
            or candidate.suffix.lower() in {".cue", ".log", ".m3u", ".m3u8"}
            or candidate.name.lower() in {"dynamic range.txt", "dr.txt"}
        )
    ]


def _dedupe_existing(paths: list[Path], source: Path) -> list[Path]:
    seen = {source}
    result: list[Path] = []
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        result.append(path)
    return result


def _target_for_source(item: ParsedMediaFile, primary_target: Path, source: Path) -> Path:
    primary_source = item.path.expanduser().resolve()
    if source == primary_source:
        return primary_target
    if source.parent == primary_source.parent and source.name.startswith(primary_source.stem):
        suffix = source.name[len(primary_source.stem):]
        return primary_target.parent / f"{primary_target.stem}{suffix}"
    if item.media_type == "tv" and source.parent == primary_source.parent.parent:
        return primary_target.parent.parent / source.name
    if item.media_type == "tv" and source.stem.lower().startswith("season"):
        return primary_target.parent.parent / source.name
    return primary_target.parent / source.name


def apply_rename_operations(plan: RenamePlan) -> list[RenameOperation]:
    if plan.conflicts:
        raise ValueError("Cannot apply rename plan with conflicts")
    applied: list[RenameOperation] = []
    for operation in plan.actionable:
        operation.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(operation.source), str(operation.target))
        applied.append(operation)
    remove_empty_source_dirs(applied)
    return applied


def apply_rename_plan(plan: RenamePlan) -> int:
    return len(apply_rename_operations(plan))


def remove_empty_source_dirs(applied: list[RenameOperation]) -> None:
    for operation in sorted(applied, key=lambda item: len(item.source.parts), reverse=True):
        directory = operation.source.parent
        while True:
            try:
                directory.rmdir()
            except OSError:
                break
            if directory.parent == directory:
                break
            directory = directory.parent
