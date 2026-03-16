"""Shared CLI helpers — formatting, parallel scan, flexible path lookup."""

from __future__ import annotations

import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from uom.core.scanner import ScanResult

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def fmt_size(n: int | float) -> str:
    """Format bytes into human-readable size."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MB"
    if n < 1024**3 * 1024:
        return f"{n / 1024**3:.2f} GB"
    return f"{n / 1024**4:.2f} TB"


def fmt_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Flexible path lookup (backward-compat relative + absolute)
# ---------------------------------------------------------------------------


def find_media_by_path(repo, path: Path, library_root: str) -> object | None:
    """Look up media by relative path first, then absolute (backward compat)."""
    rel_path = os.path.relpath(str(path.resolve()), library_root)
    media = repo.get_media_by_path(rel_path)
    if not media:
        media = repo.get_media_by_path(str(path.resolve()))
    return media


# ---------------------------------------------------------------------------
# Parallel scan helper (shared by scan, import, db sync)
# ---------------------------------------------------------------------------


def parallel_scan(
    files: list[Path],
    *,
    compute_hash: bool = True,
    jobs: int = 0,
    label: str = "Scanning",
) -> tuple[list[ScanResult], int]:
    """Run scan_and_extract in parallel via ProcessPoolExecutor.

    Returns (results, error_count).
    """
    from uom.core.scanner import process_pool_worker

    num_workers = jobs if jobs > 0 else min(mp.cpu_count(), 8)
    work_items = [(str(p.resolve()), compute_hash) for p in files]
    results: list[ScanResult] = []
    errors = 0

    if not work_items:
        return results, errors

    click.echo(f"Using {num_workers} worker process(es).")

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(process_pool_worker, item): item for item in work_items}
        with click.progressbar(length=len(futures), label=label) as bar:
            for future in as_completed(futures):
                result = future.result()
                if result.error:
                    errors += 1
                    click.echo(f"\n  [WARN] {result.path}: {result.error}", err=True)
                else:
                    results.append(result)
                bar.update(1)

    return results, errors


# ---------------------------------------------------------------------------
# Scan summary (shared by scan, import)
# ---------------------------------------------------------------------------


def print_scan_summary(results: list[ScanResult], errors: int = 0) -> None:
    """Print a detailed summary of scan results."""
    if not results:
        return

    # Counters by media type
    photos, videos, audios = [], [], []
    for r in results:
        if r.media_type == "photo":
            photos.append(r)
        elif r.media_type == "video":
            videos.append(r)
        elif r.media_type == "audio":
            audios.append(r)

    total_size = sum(r.file_size for r in results)
    photo_size = sum(r.file_size for r in photos)
    video_size = sum(r.file_size for r in videos)
    audio_size = sum(r.file_size for r in audios)

    # Missing metadata
    missing_date = [r for r in results if not r.md_date_taken]
    missing_camera = [r for r in results if not r.md_camera_model]
    missing_gps = [r for r in results if r.md_gps_lat is None]
    missing_resolution = [r for r in results if r.md_width is None]

    # Camera breakdown
    cameras: dict[str, int] = {}
    for r in results:
        if r.md_camera_model:
            key = r.md_camera_model
            if r.md_camera_make and r.md_camera_make.lower() not in r.md_camera_model.lower():
                key = f"{r.md_camera_make} {r.md_camera_model}"
            cameras[key] = cameras.get(key, 0) + 1

    # Date range
    dates = [r.md_date_taken for r in results if r.md_date_taken]
    date_range = ""
    if dates:
        dates.sort()
        earliest = dates[0][:10]  # YYYY-MM-DD
        latest = dates[-1][:10]
        if earliest == latest:
            date_range = earliest
        else:
            date_range = f"{earliest} ~ {latest}"

    # Video duration
    video_duration = sum(r.md_duration or 0 for r in videos)

    # Print summary
    click.echo()
    click.secho("─── Scan Summary ───────────────────────────────────────", fg="cyan")

    # By type
    click.echo(f"  📸 Photos : {len(photos):>5}  ({fmt_size(photo_size)})")
    click.echo(f"  🎬 Videos : {len(videos):>5}  ({fmt_size(video_size)})")
    if audios:
        click.echo(f"  🎵 Audio  : {len(audios):>5}  ({fmt_size(audio_size)})")
    click.echo(f"  {'─' * 30}")
    click.echo(f"  📁 Total  : {len(results):>5}  ({fmt_size(total_size)})")

    if video_duration > 0:
        click.echo(f"  ⏱️  Video duration: {fmt_duration(video_duration)}")

    if date_range:
        click.echo(f"  📅 Date range: {date_range}")

    # Missing metadata
    if missing_date or missing_camera or missing_gps:
        click.echo()
        click.secho("  ⚠️  Missing metadata:", fg="yellow")
        if missing_date:
            click.echo(f"     • No date taken: {len(missing_date)} file(s)")
        if missing_camera:
            click.echo(f"     • No camera info: {len(missing_camera)} file(s)")
        if missing_gps:
            click.echo(f"     • No GPS: {len(missing_gps)} file(s)")
        if missing_resolution:
            click.echo(f"     • No resolution: {len(missing_resolution)} file(s)")

    # Top cameras
    if cameras:
        click.echo()
        click.echo("  📷 Cameras:")
        sorted_cams = sorted(cameras.items(), key=lambda x: -x[1])
        for cam, cnt in sorted_cams[:5]:
            click.echo(f"     • {cam}: {cnt}")
        if len(cameras) > 5:
            click.echo(f"     • ... and {len(cameras) - 5} more")

    # Errors
    if errors:
        click.echo()
        click.secho(f"  ❌ Errors: {errors} file(s) failed to scan", fg="red")

    click.secho("────────────────────────────────────────────────────────", fg="cyan")
