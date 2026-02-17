"""uom scan — discover and ingest media files into the database (parallel)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from uom.cli import Context, pass_ctx
from uom.cli._utils import find_media_by_path, parallel_scan
from uom.core.scanner import save_scan_result

# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--no-hash", is_flag=True, help="Skip SHA-256 hash computation (faster).")
@click.option("--embed", is_flag=True, help="Generate CLIP embeddings during scan.")
@click.option(
    "--type",
    "media_type",
    type=click.Choice(["photo", "video", "audio"]),
    help="Filter by media type (e.g. video only).",
)
@click.option("--force", is_flag=True, help="Force re-scan of all files even if unchanged.")
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=0,
    show_default=True,
    help="Worker processes (0 = auto, based on CPU count).",
)
@pass_ctx
def scan(
    ctx: Context,
    directory: Path,
    no_hash: bool,
    embed: bool,
    media_type: str | None,
    force: bool,
    jobs: int,
) -> None:
    """Scan a directory and ingest media files into the database."""
    from uom.config import AUDIO_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
    from uom.core.scanner import discover_media

    repo = ctx.repo
    library_root = ctx.db_path.resolve().parent

    # Determineallowed extensions based on type filter
    allowed = None
    if media_type == "photo":
        allowed = PHOTO_EXTENSIONS
    elif media_type == "video":
        allowed = VIDEO_EXTENSIONS
    elif media_type == "audio":
        allowed = AUDIO_EXTENSIONS

    # Phase 1: discover files
    click.echo(f"Scanning: {directory.resolve()}")
    if media_type:
        click.echo(f"Filter: {media_type} only")

    files = list(discover_media(directory, allowed_extensions=allowed))
    click.echo(f"Found {len(files)} media file(s).")

    if not files:
        return

    # Filter out files that haven't changed
    to_scan: list[Path] = []
    click.echo("Checking for changes...")

    skipped = 0
    with click.progressbar(files) as bar:
        for path in bar:
            if not force:
                existing = find_media_by_path(repo, path, str(library_root))
                if existing:
                    stat = path.stat()
                    if existing.file_size == stat.st_size:
                        if existing.id:
                            md = repo.get_metadata(existing.id)
                            if md and md.date_taken:
                                skipped += 1
                                continue
            to_scan.append(path)

    if skipped > 0:
        click.echo(f"Skipped {skipped} unchanged file(s).")

    click.echo(f"{len(to_scan)} file(s) to process.\n")

    if not to_scan:
        click.echo("Nothing to do.")
        if embed:
            click.echo("\nGenerating CLIP embeddings...")
            _generate_embeddings(repo)
        return

    # Phase 2: parallel scan + metadata extraction
    results, errors = parallel_scan(
        to_scan, compute_hash=not no_hash, jobs=jobs, label="Scanning & extracting metadata"
    )

    # Phase 3: bulk write to DB (single-threaded, fast)
    new_count = 0
    updated_count = 0
    with click.progressbar(results, label="Writing to database") as bar:
        for r in bar:
            existing = find_media_by_path(repo, Path(r.path), str(library_root))

            save_scan_result(repo, r, library_root=library_root)

            if existing:
                updated_count += 1
            else:
                new_count += 1

    click.echo(f"\nDone. Added {new_count} new, updated {updated_count} existing.")
    if errors:
        click.echo(f"  {errors} file(s) had errors.")

    # Phase 4 (optional): embeddings
    if embed:
        click.echo("\nGenerating CLIP embeddings...")
        _generate_embeddings(repo, library_root=library_root)


def _generate_embeddings(repo: Any, library_root: Path | str | None = None) -> None:
    """Generate embeddings for media without one."""
    from uom.core.embeddings import generate_embeddings

    pending = repo.media_without_embedding()
    pending = [m for m in pending if m.media_type.value == "photo"]
    if not pending:
        click.echo("No new images to embed.")
        return

    click.echo(f"Embedding {len(pending)} image(s)...")
    with click.progressbar(length=len(pending), label="Embedding") as bar:
        done = generate_embeddings(
            repo, progress_cb=lambda _: bar.update(1), library_root=library_root
        )
    click.echo(f"Embedded {done} image(s).")
