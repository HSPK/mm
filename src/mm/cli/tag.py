"""uom tag — manage tags on media files."""

from __future__ import annotations

import os
from pathlib import Path

import click

from mm.cli import Context, pass_ctx
from mm.config import resolve_media_path


@click.group()
def tag() -> None:
    """Manage tags on media files."""


@tag.command("add")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-t", "--tag", "tag_names", required=True, multiple=True, help="Tag(s) to add."
)
@pass_ctx
def tag_add(ctx: Context, path: Path, tag_names: tuple[str, ...]) -> None:
    """Add tag(s) to a file or all files under a directory."""
    from mm.core.tagger import add_tags

    repo = ctx.repo
    library_root = str(ctx.db_path.resolve().parent)
    targets = _resolve_targets(repo, path, library_root)

    if not targets:
        click.echo("No media found in database for this path. Run 'uom scan' first.")
        return

    for media_id in targets:
        add_tags(repo, media_id, list(tag_names))

    click.echo(f"Added tag(s) {', '.join(tag_names)} to {len(targets)} file(s).")


@tag.command("remove")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-t", "--tag", "tag_names", required=True, multiple=True, help="Tag(s) to remove."
)
@pass_ctx
def tag_remove(ctx: Context, path: Path, tag_names: tuple[str, ...]) -> None:
    """Remove tag(s) from a file or all files under a directory."""
    from mm.core.tagger import remove_tags

    repo = ctx.repo
    library_root = str(ctx.db_path.resolve().parent)
    targets = _resolve_targets(repo, path, library_root)

    if not targets:
        click.echo("No media found in database for this path.")
        return

    for media_id in targets:
        remove_tags(repo, media_id, list(tag_names))

    click.echo(f"Removed tag(s) {', '.join(tag_names)} from {len(targets)} file(s).")


@tag.command("list")
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@pass_ctx
def tag_list(ctx: Context, path: Path | None) -> None:
    """List tags — for a specific file, or all tags in the database."""
    repo = ctx.repo

    if path:
        library_root = str(ctx.db_path.resolve().parent)
        rel_path = os.path.relpath(str(path.resolve()), library_root)
        media = repo.get_media_by_path(rel_path)
        if not media:
            media = repo.get_media_by_path(str(path.resolve()))  # backward compat
        if not media or media.id is None:
            click.echo("File not found in database.")
            return
        tags_info = repo.tags_for_media(media.id)
        if not tags_info:
            click.echo("No tags.")
            return
        for t, conf in tags_info:
            conf_str = f" ({conf:.2f})" if conf < 1.0 else ""
            click.echo(f"  {t.name}{conf_str}  [{t.source.value}]")
    else:
        all_tags = repo.all_tags()
        if not all_tags:
            click.echo("No tags in database.")
            return
        click.echo(f"Tags ({len(all_tags)}):")
        for t in all_tags:
            click.echo(f"  {t.name}  [{t.source.value}]")


@tag.command("auto")
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--rules/--no-rules", default=True, help="Apply rule-based tags.")
@click.option(
    "--clip", is_flag=True, help="Apply CLIP-based auto-tags (requires torch)."
)
@click.option(
    "--threshold", default=0.25, show_default=True, help="CLIP confidence threshold."
)
@pass_ctx
def tag_auto(
    ctx: Context, directory: Path, rules: bool, clip: bool, threshold: float
) -> None:
    """Automatically tag media via rules and/or CLIP."""
    from mm.core.tagger import apply_clip_tags, apply_rule_tags

    repo = ctx.repo
    media_list = repo.all_media()
    # Filter to files under directory
    dir_str = str(directory.resolve())
    library_root = str(ctx.db_path.resolve().parent)
    media_list = [
        m
        for m in media_list
        if resolve_media_path(m.path, library_root).startswith(dir_str)
    ]

    if not media_list:
        click.echo(
            "No media found in database under this directory. Run 'uom scan' first."
        )
        return

    if rules:
        click.echo(f"Applying rule-based tags to {len(media_list)} file(s)...")
        with click.progressbar(media_list, label="Rule-tagging") as bar:
            for media in bar:
                # Resolve relative path for core module access
                media.path = resolve_media_path(media.path, library_root)
                md = repo.get_metadata(media.id) if media.id else None  # type: ignore[arg-type]
                apply_rule_tags(repo, media, md)
        click.echo("Rule-based tagging done.")

    if clip:
        photos = [m for m in media_list if m.media_type.value == "photo"]
        click.echo(f"\nApplying CLIP auto-tags to {len(photos)} photo(s)...")
        with click.progressbar(photos, label="CLIP-tagging") as bar:
            for media in bar:
                media.path = resolve_media_path(media.path, library_root)
                apply_clip_tags(repo, media, threshold=threshold)
        click.echo("CLIP auto-tagging done.")


@tag.command("stats")
@pass_ctx
def tag_stats(ctx: Context) -> None:
    """Show tag usage statistics."""
    repo = ctx.repo
    stats = repo.tag_stats()
    if not stats:
        click.echo("No tags in database.")
        return
    click.echo(f"{'Tag':<30} {'Count':>8}")
    click.echo("-" * 40)
    for name, count in stats:
        click.echo(f"  {name:<28} {count:>8}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_targets(repo, path: Path, library_root: str | None = None) -> list[int]:
    """Return media IDs for a file or all files under a directory."""
    resolved = str(path.resolve())
    if library_root is None:
        library_root = str(Path.cwd())

    if path.is_file():
        rel_path = os.path.relpath(resolved, library_root)
        media = repo.get_media_by_path(rel_path)
        if not media:
            media = repo.get_media_by_path(resolved)  # backward compat
        return [media.id] if media and media.id is not None else []
    else:
        all_media = repo.all_media()
        return [
            m.id
            for m in all_media
            if m.id is not None
            and resolve_media_path(m.path, library_root).startswith(resolved)
        ]
