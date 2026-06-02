from __future__ import annotations

import click

from mm.cli import ui


@click.command()
@click.option("--tag", "tag_names", multiple=True, help="Filter by tag(s). Repeat for AND logic.")
@click.option("--tag-or", is_flag=True, help="Use OR logic for tags instead of AND.")
@click.option("-k", "--top-k", default=10, show_default=True, help="Number of results.")
def search(
    tag_names: tuple[str, ...],
    tag_or: bool,
    top_k: int,
) -> None:
    """Search media by tags."""
    from mm.cli import active_library
    from mm.media.search import (
        NoSearchCriteria,
        NoTagMatches,
        search_media,
    )

    db = active_library().db
    try:
        result = search_media(
            db,
            tag_names=list(tag_names),
            match_all_tags=not tag_or,
            top_k=top_k,
        )
    except NoSearchCriteria:
        ui.warning("Provide at least one --tag")
        return
    except NoTagMatches:
        ui.warning("No media matches the given tag(s).")
        return

    if result.tag_candidates is not None:
        ui.info(f"Tag filter: {result.tag_candidates:,} candidate(s)")

    ui.print_table(
        [ui.Column("Path", max_width=80), ui.Column("Tags", max_width=40)],
        [[ui.path(item.path), item.tags or "-"] for item in result.items],
        title=f"Results ({len(result.items):,} files)",
    )
