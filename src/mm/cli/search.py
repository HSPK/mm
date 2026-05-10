from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui


@click.command()
@click.option(
    "--image",
    "image_path",
    type=click.Path(exists=True, path_type=Path),
    help="Search by image similarity.",
)
@click.option("--text", "text_query", type=str, help="Search by text description.")
@click.option("--tag", "tag_names", multiple=True, help="Filter by tag(s). Repeat for AND logic.")
@click.option("--tag-or", is_flag=True, help="Use OR logic for tags instead of AND.")
@click.option("-k", "--top-k", default=10, show_default=True, help="Number of results.")
def search(
    image_path: Path | None,
    text_query: str | None,
    tag_names: tuple[str, ...],
    tag_or: bool,
    top_k: int,
) -> None:
    """Search media by image similarity, text description, or tags."""
    from mm.cli import get_repo

    repo = get_repo()

    # Tag pre-filter
    filter_ids: set[int] | None = None
    if tag_names:
        ids = repo.media_ids_by_tags(list(tag_names), match_all=not tag_or)
        if not ids:
            ui.warning("No media matches the given tag(s).")
            return
        filter_ids = set(ids)
        ui.info(f"Tag filter: {len(filter_ids):,} candidate(s)")

    # Vector search
    if image_path or text_query:
        from mm.db.vector_store import VectorStore

        vs = VectorStore(repo)
        n = vs.load()
        if n == 0:
            ui.warning("No embeddings found. Run an embedding scan before vector search.")
            return

        if image_path:
            from mm.core.embeddings import encode_image_from_path

            query_vec = encode_image_from_path(image_path)
            if query_vec is None:
                ui.error(f"Failed to encode image: {image_path}")
                return
            query_vec = query_vec.flatten()
            ui.key_values("Search", [("Image", ui.path(image_path)), ("Embeddings", f"{n:,}")])
        else:
            from mm.core.embeddings import encode_text

            assert text_query is not None
            query_vec = encode_text(text_query).flatten()
            ui.key_values("Search", [("Text", text_query), ("Embeddings", f"{n:,}")])

        results = vs.search(query_vec, top_k=top_k, filter_ids=filter_ids)

        if not results:
            ui.warning("No results found.")
            return

        rows: list[list[object]] = []
        for rank, (media_id, sim) in enumerate(results, 1):
            media = repo.get_media_by_id(media_id)
            if media:
                tags_info = repo.tags_for_media(media_id)
                tag_str = ", ".join(t.name for t, _ in tags_info) if tags_info else ""
                rows.append([str(rank), f"{sim:.3f}", ui.path(media.path), tag_str or "-"])
        ui.print_table(
            [
                ui.Column("#", justify="right"),
                ui.Column("Score", justify="right"),
                ui.Column("Path", max_width=72),
                ui.Column("Tags", max_width=36),
            ],
            rows,
            title="Search Results",
        )

    elif tag_names:
        # Tag-only search (no vector)
        assert filter_ids is not None
        rows = []
        for media_id in sorted(filter_ids):
            media = repo.get_media_by_id(media_id)
            if media:
                tags_info = repo.tags_for_media(media_id)
                tag_str = ", ".join(t.name for t, _ in tags_info) if tags_info else ""
                rows.append([ui.path(media.path), tag_str or "-"])
        ui.print_table(
            [ui.Column("Path", max_width=80), ui.Column("Tags", max_width=40)],
            rows,
            title=f"Results ({len(filter_ids):,} files)",
        )
    else:
        ui.warning("Provide at least one of: --image, --text, or --tag")
