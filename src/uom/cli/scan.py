"""uom scan — discover and ingest media files into the database (parallel)."""

from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from uom.cli import Context, pass_ctx

# ---------------------------------------------------------------------------
# Worker payload — must be picklable (top-level dataclass + function)
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    """Serialisable result returned by each worker process."""

    path: str
    filename: str
    extension: str
    media_type: str
    file_size: int
    file_hash: str
    created_at: str  # ISO format or ""
    modified_at: str
    # metadata fields
    md_date_taken: str
    md_camera_make: str
    md_camera_model: str
    md_lens_model: str
    md_focal_length: float | None
    md_aperture: float | None
    md_shutter_speed: str
    md_iso: int | None
    md_width: int | None
    md_height: int | None
    md_duration: float | None
    md_gps_lat: float | None
    md_gps_lon: float | None
    md_orientation: int | None
    error: str = ""


def _scan_one(args: tuple[str, bool]) -> ScanResult:
    """Process a single file — runs in a worker process."""
    path_str, compute_hash = args
    path = Path(path_str)
    try:
        from uom.core.metadata import extract_metadata
        from uom.core.scanner import scan_file

        media = scan_file(path, compute_hash=compute_hash)

        # Extract metadata (media_id=0 placeholder — will be set after DB insert)
        md = extract_metadata(path, 0)

        return ScanResult(
            path=media.path,
            filename=media.filename,
            extension=media.extension,
            media_type=media.media_type.value,
            file_size=media.file_size,
            file_hash=media.file_hash,
            created_at=media.created_at.isoformat() if media.created_at else "",
            modified_at=media.modified_at.isoformat() if media.modified_at else "",
            md_date_taken=md.date_taken.isoformat() if md.date_taken else "",
            md_camera_make=md.camera_make,
            md_camera_model=md.camera_model,
            md_lens_model=md.lens_model,
            md_focal_length=md.focal_length,
            md_aperture=md.aperture,
            md_shutter_speed=md.shutter_speed,
            md_iso=md.iso,
            md_width=md.width,
            md_height=md.height,
            md_duration=md.duration,
            md_gps_lat=md.gps_lat,
            md_gps_lon=md.gps_lon,
            md_orientation=md.orientation,
        )
    except Exception as e:
        return ScanResult(
            path=path_str,
            filename=path.name,
            extension=path.suffix.lower(),
            media_type="photo",
            file_size=0,
            file_hash="",
            created_at="",
            modified_at="",
            md_date_taken="",
            md_camera_make="",
            md_camera_model="",
            md_lens_model="",
            md_focal_length=None,
            md_aperture=None,
            md_shutter_speed="",
            md_iso=None,
            md_width=None,
            md_height=None,
            md_duration=None,
            md_gps_lat=None,
            md_gps_lon=None,
            md_orientation=None,
            error=str(e),
        )


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
    from datetime import datetime

    from uom.core.scanner import discover_media
    from uom.db.models import MediaType
    from uom.db.repository import Media, Metadata

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
            continue
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
            media = Media(
                path=r.path,
                filename=r.filename,
                extension=r.extension,
                media_type=MediaType(r.media_type),
                file_size=r.file_size,
                file_hash=r.file_hash,
                created_at=datetime.fromisoformat(r.created_at) if r.created_at else None,
                modified_at=datetime.fromisoformat(r.modified_at) if r.modified_at else None,
            )
            media_id = repo.upsert_media(media)

            md = Metadata(
                media_id=media_id,
                date_taken=datetime.fromisoformat(r.md_date_taken) if r.md_date_taken else None,
                camera_make=r.md_camera_make,
                camera_model=r.md_camera_model,
                lens_model=r.md_lens_model,
                focal_length=r.md_focal_length,
                aperture=r.md_aperture,
                shutter_speed=r.md_shutter_speed,
                iso=r.md_iso,
                width=r.md_width,
                height=r.md_height,
                duration=r.md_duration,
                gps_lat=r.md_gps_lat,
                gps_lon=r.md_gps_lon,
                orientation=r.md_orientation,
            )
            repo.upsert_metadata(md)

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
