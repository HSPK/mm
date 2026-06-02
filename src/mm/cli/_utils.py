"""Shared CLI helpers — scan summaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mm.cli import ui
from mm.utils.formatting import fmt_duration, fmt_size

if TYPE_CHECKING:
    from mm.media.scanner import ScanResult

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
            caption=(f"... and {len(cameras) - 5} more" if len(cameras) > 5 else None),
        )

    # Errors
    if errors:
        ui.error(f"{errors} file(s) failed to scan")
