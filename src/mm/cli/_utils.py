"""Shared CLI helpers — formatting, parallel scan, flexible path lookup."""

from __future__ import annotations

import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from mm.cli import ui

if TYPE_CHECKING:
    from mm.core.scanner import ScanResult

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
    from mm.core.scanner import process_pool_worker

    num_workers = jobs if jobs > 0 else min(mp.cpu_count(), 8)
    work_items = [(str(p.resolve()), compute_hash) for p in files]
    results: list[ScanResult] = []
    errors = 0

    if not work_items:
        return results, errors

    ui.info(f"Using {num_workers} worker process(es).")

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(process_pool_worker, item): item for item in work_items}
        with ui.progress(label, len(futures)) as bar:
            for future in as_completed(futures):
                result = future.result()
                if result.error:
                    errors += 1
                    ui.warning(f"{result.media.path}: {result.error}", stderr=True)
                else:
                    results.append(result)
                bar.advance()

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
        mt = (
            r.media.media_type.value if hasattr(r.media.media_type, "value") else r.media.media_type
        )
        if mt == "photo":
            photos.append(r)
        elif mt == "video":
            videos.append(r)
        elif mt == "audio":
            audios.append(r)

    total_size = sum(r.media.file_size for r in results)
    photo_size = sum(r.media.file_size for r in photos)
    video_size = sum(r.media.file_size for r in videos)
    audio_size = sum(r.media.file_size for r in audios)

    # Missing metadata
    missing_date = [r for r in results if not r.metadata.date_taken]
    missing_camera = [r for r in results if not r.metadata.camera_model]
    missing_gps = [r for r in results if r.metadata.gps_lat is None]
    missing_resolution = [r for r in results if r.metadata.width is None]

    # Camera breakdown
    cameras: dict[str, int] = {}
    for r in results:
        if r.metadata.camera_model:
            key = r.metadata.camera_model
            if (
                r.metadata.camera_make
                and r.metadata.camera_make.lower() not in r.metadata.camera_model.lower()
            ):
                key = f"{r.metadata.camera_make} {r.metadata.camera_model}"
            cameras[key] = cameras.get(key, 0) + 1

    # Date range
    dates = [r.metadata.date_taken for r in results if r.metadata.date_taken]
    date_range = ""
    if dates:
        dates.sort()
        earliest = dates[0].strftime("%Y-%m-%d")
        latest = dates[-1].strftime("%Y-%m-%d")
        if earliest == latest:
            date_range = earliest
        else:
            date_range = f"{earliest} ~ {latest}"

    # Video duration
    video_duration = sum(r.metadata.duration or 0 for r in videos)

    ui.section("Scan Summary")
    type_rows: list[list[object]] = [
        ["Photos", f"{len(photos):,}", fmt_size(photo_size)],
        ["Videos", f"{len(videos):,}", fmt_size(video_size)],
    ]
    if audios:
        type_rows.append(["Audio", f"{len(audios):,}", fmt_size(audio_size)])
    type_rows.append(["Total", f"{len(results):,}", fmt_size(total_size)])
    ui.print_table(
        [
            ui.Column("Type"),
            ui.Column("Files", justify="right"),
            ui.Column("Size", justify="right"),
        ],
        type_rows,
    )

    facts: list[tuple[str, object]] = []
    if video_duration > 0:
        facts.append(("Video duration", fmt_duration(video_duration)))

    if date_range:
        facts.append(("Date range", date_range))

    if facts:
        ui.key_values("Details", facts)

    # Missing metadata
    if missing_date or missing_camera or missing_gps:
        missing_rows: list[list[object]] = []
        if missing_date:
            missing_rows.append(["Date taken", f"{len(missing_date):,}"])
        if missing_camera:
            missing_rows.append(["Camera info", f"{len(missing_camera):,}"])
        if missing_gps:
            missing_rows.append(["GPS", f"{len(missing_gps):,}"])
        if missing_resolution:
            missing_rows.append(["Resolution", f"{len(missing_resolution):,}"])
        ui.print_table(
            [ui.Column("Missing metadata"), ui.Column("Files", justify="right")],
            missing_rows,
            title="Needs Attention",
        )

    # Top cameras
    if cameras:
        sorted_cams = sorted(cameras.items(), key=lambda x: -x[1])
        camera_rows = [[cam, f"{cnt:,}"] for cam, cnt in sorted_cams[:5]]
        ui.print_table(
            [ui.Column("Camera", max_width=48), ui.Column("Files", justify="right")],
            camera_rows,
            title="Top Cameras",
            caption=(
                f"... and {len(cameras) - 5} more" if len(cameras) > 5 else None
            ),
        )

    # Errors
    if errors:
        ui.error(f"{errors} file(s) failed to scan")
