from __future__ import annotations

import click

from mm.cli import ui
from mm.cli.db import db
from mm.config import get_config
from mm.io import local_storage
from mm.utils.formatting import fmt_size


@db.command("thumbnails")
@click.option("--size", "sizes", multiple=True, help="Thumbnail size to build. Repeatable.")
@click.option("--force", is_flag=True, help="Regenerate existing thumbnails.")
@click.option("-j", "--jobs", type=int, default=0, help="Worker count (0 = auto).")
def db_thumbnails(sizes: tuple[str, ...], force: bool, jobs: int) -> None:
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
                    ("Mode", "force" if force else "missing/stale"),
                ],
            )

            progress_total = active.db.media.count() * len(
                selected_sizes or get_config().thumbnails.sizes
            )
            with ui.progress("Building thumbnails", progress_total) as bar:
                result = build_thumbnail_cache(
                    active.db,
                    active.config.library_root,
                    active.config.library_id,
                    sizes=selected_sizes,
                    force=force,
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
                ("Size", fmt_size(after.total_size)),
                ("Delta", fmt_size(after.total_size - before.total_size)),
            ],
        )
    finally:
        active.close()
