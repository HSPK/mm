"""uom scan — discover and ingest media files into the database (parallel)."""

from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import click

from uom.cli import Context, pass_ctx
from uom.core.scanner import ScanResult, process_pool_worker, save_scan_result

# ---------------------------------------------------------------------------
# Worker payload — must be picklable (top-level dataclass + function)
# ---------------------------------------------------------------------------


# Alias required for pickling safety if using ProcessPoolExecutor
_scan_one = process_pool_worker


# ---------------------------------------------------------------------------

# CLI command
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--no-hash", is_flag=True, help="Skip SHA-256 hash computation (faster).")
@click.option("--embed", is_flag=True, help="Generate CLIP embeddings during scan.")
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=0,
    show_default=True,
    help="Worker processes (0 = auto, based on CPU count).",
)
@pass_ctx
def scan(ctx: Context, directory: Path, no_hash: bool, embed: bool, jobs: int) -> None:
    """Scan a directory and ingest media files into the database."""
    from uom.core.scanner import discover_media

    repo = ctx.repo

    # Phase 1: discover files
    click.echo(f"Scanning: {directory.resolve()}")
    files = list(discover_media(directory))
    click.echo(f"Found {len(files)} media file(s).")

    if not files:
        return

    # Filter out files that haven't changed
    to_scan: list[Path] = []
    for path in files:
        existing = repo.get_media_by_path(str(path.resolve()))
        if existing and existing.file_size == path.stat().st_size:
            # If metadata (specifically date_taken) is missing, we re-scan
            if existing.id:
                md = repo.get_metadata(existing.id)
                if md and md.date_taken:
                    continue  # Skip only if we have metadata + valid date
        to_scan.append(path)

    click.echo(
        f"{len(to_scan)} file(s) to process ({len(files) - len(to_scan)} unchanged, skipped).\n"
    )

    if not to_scan:
        click.echo("Nothing to do.")
        if embed:
            click.echo("\nGenerating CLIP embeddings...")
            _generate_embeddings(repo)
        return

    # Phase 2: parallel scan + metadata extraction
    num_workers = jobs if jobs > 0 else min(mp.cpu_count(), 8)
    click.echo(f"Using {num_workers} worker process(es).")

    work_items = [(str(p.resolve()), not no_hash) for p in to_scan]
    results: list[ScanResult] = []
    errors = 0

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(_scan_one, item): item for item in work_items}
        with click.progressbar(length=len(futures), label="Scanning & extracting metadata") as bar:
            for future in as_completed(futures):
                result = future.result()
                if result.error:
                    errors += 1
                    click.echo(f"\n  [WARN] {result.path}: {result.error}", err=True)
                else:
                    results.append(result)
                bar.update(1)

    # Phase 3: bulk write to DB (single-threaded, fast)
    new_count = 0
    updated_count = 0
    with click.progressbar(results, label="Writing to database") as bar:
        for r in bar:
            existing = repo.get_media_by_path(r.path)

            save_scan_result(repo, r)

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
        _generate_embeddings(repo)


def _generate_embeddings(repo: Any) -> None:
    """Generate embeddings for media without one."""
    from uom.core.embeddings import encode_image_from_path, get_clip_model
    from uom.db.repository import Embedding
    from uom.db.vector_store import vector_to_bytes

    media_list = repo.media_without_embedding()
    media_list = [m for m in media_list if m.media_type.value == "photo"]

    if not media_list:
        click.echo("No new images to embed.")
        return

    click.echo(f"Embedding {len(media_list)} image(s)...")
    model, preprocess, _, device = get_clip_model()

    done = 0
    with click.progressbar(media_list, label="Embedding") as bar:
        for media in bar:
            vec = encode_image_from_path(Path(media.path), model, preprocess, device)
            if vec is not None:
                emb = Embedding(
                    media_id=media.id,
                    vector=vector_to_bytes(vec.flatten()),
                    model=f"{model.__class__.__name__}",
                )
                repo.upsert_embedding(emb)
                done += 1

    click.echo(f"Embedded {done} image(s).")
