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
