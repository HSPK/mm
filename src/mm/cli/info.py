from __future__ import annotations

from pathlib import Path

import click

from mm.cli._utils import fmt_size as _fmt_size
from mm.db.dto import Metadata


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def info(file: Path) -> None:
    """Show metadata for a single media file."""
    from mm.core.metadata import check_tools
    from mm.core.scanner import scan_and_extract

    missing = check_tools()
    if missing:
        click.secho(
            f"Warning: {', '.join(missing)} not found — metadata may be incomplete."
            " Install via: brew install exiftool ffmpeg",
            fg="yellow",
            err=True,
        )

    res = scan_and_extract(file, compute_hash=True)

    if res.error:
        click.secho(f"Error scanning file: {res.error}", fg="red")
        return

    m = res.media
    click.echo(f"File     : {m.path}")
    click.echo(f"Type     : {m.media_type.value}")
    click.echo(f"Size     : {_fmt_size(m.file_size)}")
    click.echo(f"Hash     : {m.file_hash}")
    click.echo(f"Modified : {m.modified_at}")
    click.echo()

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

    click.echo("Metadata:")
    for label, value in fields:
        if value is not None:
            click.echo(f"  {label:<15} {value}")
