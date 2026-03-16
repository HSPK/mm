"""uom search — vector search (image/text) and tag search."""

from __future__ import annotations

from pathlib import Path

import click

from uom.cli import Context, pass_ctx


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
@pass_ctx
def search(
    ctx: Context,
    image_path: Path | None,
    text_query: str | None,
    tag_names: tuple[str, ...],
    tag_or: bool,
    top_k: int,
) -> None:
    """Search media by image similarity, text description, or tags."""
    repo = ctx.repo

    # Tag pre-filter
    filter_ids: set[int] | None = None
    if tag_names:
        ids = repo.media_ids_by_tags(list(tag_names), match_all=not tag_or)
        if not ids:
            click.echo("No media matches the given tag(s).")
            return
        filter_ids = set(ids)
        click.echo(f"Tag filter: {len(filter_ids)} candidate(s)")

    # Vector search
    if image_path or text_query:
        from uom.db.vector_store import VectorStore

        vs = VectorStore(repo)
        n = vs.load()
        if n == 0:
            click.echo("No embeddings in database. Run 'uom scan --embed' first.")
            return

        if image_path:
            from uom.core.embeddings import encode_image_from_path

            query_vec = encode_image_from_path(image_path)
            if query_vec is None:
                click.echo(f"Failed to encode image: {image_path}")
                return
            query_vec = query_vec.flatten()
            click.echo(f"\nSearching by image: {image_path}\n")
        else:
            from uom.core.embeddings import encode_text

            assert text_query is not None
            query_vec = encode_text(text_query).flatten()
            click.echo(f'\nSearching by text: "{text_query}"\n')

        results = vs.search(query_vec, top_k=top_k, filter_ids=filter_ids)

        if not results:
            click.echo("No results found.")
            return

        for rank, (media_id, sim) in enumerate(results, 1):
            media = repo.get_media_by_id(media_id)
            if media:
                tags_info = repo.tags_for_media(media_id)
                tag_str = ", ".join(t.name for t, _ in tags_info) if tags_info else ""
                click.echo(f"  {rank:3d}. [{sim:.3f}] {media.path}")
                if tag_str:
                    click.echo(f"       tags: {tag_str}")

    elif tag_names:
        # Tag-only search (no vector)
        assert filter_ids is not None
        click.echo(f"\nResults ({len(filter_ids)} files):\n")
        for media_id in sorted(filter_ids):
            media = repo.get_media_by_id(media_id)
            if media:
                tags_info = repo.tags_for_media(media_id)
                tag_str = ", ".join(t.name for t, _ in tags_info) if tags_info else ""
                click.echo(f"  {media.path}")
                if tag_str:
                    click.echo(f"    tags: {tag_str}")
    else:
        click.echo("Provide at least one of: --image, --text, or --tag")
