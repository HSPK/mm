from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui
from mm.db.dto import Metadata
from mm.io import local_storage
from mm.utils.formatting import fmt_size


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--metadata-mode",
    type=click.Choice(["exiftool", "pillow"]),
    default="exiftool",
    show_default=True,
    help="Metadata extraction mode. Pillow mode extracts basic photo metadata only.",
)
def info(file: Path, metadata_mode: str) -> None:
    """Show metadata for a single media file."""
    from mm.extractor.metadata import (
        MetadataToolUnavailable,
        check_tools,
        normalize_metadata_mode,
        require_metadata_mode,
    )
    from mm.media.scanner import scan_and_extract

    try:
        normalized_metadata_mode = normalize_metadata_mode(metadata_mode)
        require_metadata_mode(normalized_metadata_mode)
    except MetadataToolUnavailable as error:
        ui.error(str(error))
        raise SystemExit(1) from error

    if normalized_metadata_mode == "pillow":
        missing = [tool for tool in check_tools() if tool != "exiftool"]
        if missing:
            ui.warning(
                f"{', '.join(missing)} not found — video/audio metadata may be incomplete. "
                "Install via: brew install ffmpeg",
                stderr=True,
            )

    res = scan_and_extract(
        file,
        compute_hash=True,
        storage=local_storage,
        metadata_mode=normalized_metadata_mode,
    )

    if res.error:
        ui.error(f"Error scanning file: {res.error}")
        return

    m = res.media
    ui.key_values(
        "File",
        [
            ("Path", ui.path(m.path)),
            ("Type", m.media_type.value),
            ("Size", fmt_size(m.file_size)),
            ("Hash", m.file_hash),
            ("Modified", m.modified_at),
        ],
    )

    print_metadata(res.metadata)


def print_metadata(md: Metadata) -> None:
    """Print metadata fields in a readable format."""
    fields = [
        ("Date taken", md.date_taken),
        ("Camera", f"{md.camera_make} {md.camera_model}".strip() or None),
        ("Lens", md.lens_model or None),
        ("Focal length", f"{md.focal_length} mm" if md.focal_length else None),
        ("Aperture", f"f/{md.aperture}" if md.aperture else None),
        ("Shutter", md.shutter_speed or None),
        ("ISO", md.iso),
        ("Resolution", f"{md.width} × {md.height}" if md.width and md.height else None),
        ("Duration", f"{md.duration:.1f} s" if md.duration else None),
        ("GPS", f"{md.gps_lat}, {md.gps_lon}" if md.gps_lat and md.gps_lon else None),
        ("Orientation", md.orientation),
    ]

    rows = [(label, value) for label, value in fields if value is not None]
    if rows:
        ui.key_values("Metadata", rows)
    else:
        ui.warning("No metadata found.")
