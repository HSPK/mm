"""General formatting helpers."""

from __future__ import annotations


def fmt_size(n: int | float) -> str:
    """Format bytes into human-readable size."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MB"
    if n < 1024**4:
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
