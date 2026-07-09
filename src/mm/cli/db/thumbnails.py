from __future__ import annotations

import click

from mm.cli import ui
from mm.cli.db import db
from mm.config import get_config
from mm.io import local_storage
from mm.utils.formatting import fmt_size


@db.command("thumbnails")
@click.option("--size", "sizes", multiple=True, help="Thumbnail size to build. Repeatable.")
@click.option("--missing", is_flag=True, help="Build missing/stale thumbnails (default).")
@click.option("--videos", is_flag=True, help="Only build video thumbnails.")
@click.option("--failed", is_flag=True, help="Only retry thumbnails with failed markers.")
@click.option("--force", is_flag=True, help="Regenerate existing thumbnails.")
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
def db_thumbnails(
    sizes: tuple[str, ...],
    missing: bool,
    videos: bool,
    failed: bool,
    force: bool,
    jobs: int,
) -> None:
    """Build thumbnail cache for the active library."""
    from mm.cli import active_library
    from mm.library.thumbnails import build_thumbnail_cache, thumbnail_cache_stats

    active = active_library()
    try:
        selected_sizes = list(sizes) or None
        try:
            before = thumbnail_cache_stats(active.config.library_id, storage=local_storage)
            ui.key_values(
                "Thumbnail Build",
                [
                    ("Library", ui.path(active.config.library_root)),
                    ("Database", ui.path(active.database)),
                    ("Cache", ui.path(before.cache_dir)),
                    ("Sizes", ", ".join(selected_sizes or ["all"])),
                    ("Mode", _mode_label(missing=missing, failed=failed, force=force)),
                    ("Media", "videos" if videos else "all"),
                    ("Failed markers", f"{before.failed_count:,}"),
                ],
            )

            media_count = len([
                media
                for media in active.db.media.list()
                if media.deleted_at is None
                and (
                    media.media_type.value == "video"
                    if videos
                    else media.media_type.value in {"photo", "video"}
                )
            ])
            progress_total = media_count * len(selected_sizes or get_config().thumbnails.sizes)
            with ui.progress("Building thumbnails", progress_total) as bar:
                result = build_thumbnail_cache(
                    active.db,
                    active.config.library_root,
                    active.config.library_id,
                    sizes=selected_sizes,
                    force=force,
                    media_types={"video"} if videos else None,
                    failed_only=failed,
                    jobs=jobs,
                    storage=local_storage,
                    on_progress=lambda _result: bar.advance(),
                )
            after = thumbnail_cache_stats(active.config.library_id, storage=local_storage)
        except ValueError as error:
            ui.error(str(error))
            raise SystemExit(1) from error

        ui.success(
            f"Thumbnails ready: {result.generated:,} generated, "
            f"{result.cached:,} cached, {result.failed:,} failed."
        )
        ui.key_values(
            "Thumbnail Cache",
            [
                ("Files", f"{after.file_count:,}"),
                ("Failed markers", f"{after.failed_count:,}"),
                ("Size", fmt_size(after.total_size)),
                ("Delta", fmt_size(after.total_size - before.total_size)),
            ],
        )
    finally:
        active.close()


def _mode_label(*, missing: bool, failed: bool, force: bool) -> str:
    if failed:
        return "failed"
    if force:
        return "force"
    if missing:
        return "missing/stale"
    return "missing/stale"
