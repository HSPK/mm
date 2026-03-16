"""uom info — show metadata for a single file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from mm.cli import Context, pass_ctx
from mm.cli._utils import fmt_size as _fmt_size


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--raw", is_flag=True, help="Always extract from file (ignore database).")
@pass_ctx
def info(ctx: Context, file: Path, raw: bool) -> None:
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

    resolved = str(file.resolve())
    repo = ctx.repo

    media = None
    if not raw:
        media = repo.get_media_by_path(resolved)

    if media and media.id is not None:
        # DB Mode
        click.secho(f"Source: Database (ID: {media.id})", fg="cyan")
        click.echo(f"File     : {media.path}")
        click.echo(f"Type     : {media.media_type.value}")
        click.echo(f"Size     : {_fmt_size(media.file_size)}")
        click.echo(f"Hash     : {media.file_hash or '(not computed)'}")
        click.echo(f"Scanned  : {media.scanned_at}")
        click.echo()

        md = repo.get_metadata(media.id)
        if md:
            _print_metadata(md)
        else:
            click.echo("(no metadata in database)")

        tags_info = repo.tags_for_media(media.id)
        if tags_info:
            click.echo()
            click.echo("Tags:")
            for t, conf in tags_info:
                conf_str = f" ({conf:.2f})" if conf < 1.0 else ""
                click.echo(f"  {t.name}{conf_str}  [{t.source.value}]")
    else:
        # RAW Mode (Live extraction via shared scanner logic)
        source_label = "Disk (Live extraction)" if not raw else "Disk (Force raw)"
        click.secho(f"Source: {source_label}", fg="yellow")

        # scan_and_extract handles extraction + basic stat
        # We pass compute_hash=False to keep it fast for 'info' unless needed,
        # but user sees 'Hash' field, maybe we should just compute it to be accurate?
        # Let's compute it. It's usually fast enough for one file.
        res = scan_and_extract(file, compute_hash=True)

        if res.error:
            click.secho(f"Error scanning file: {res.error}", fg="red")
            return

        click.echo(f"File     : {res.path}")
        click.echo(f"Type     : {res.media_type}")
        click.echo(f"Size     : {_fmt_size(res.file_size)}")
        click.echo(f"Hash     : {res.file_hash}")
        click.echo(f"Modified : {res.modified_at}")
        click.echo()

        from types import SimpleNamespace

        md = SimpleNamespace(
            date_taken=res.md_date_taken,
            camera_make=res.md_camera_make,
            camera_model=res.md_camera_model,
            lens_model=res.md_lens_model,
            focal_length=res.md_focal_length,
            aperture=res.md_aperture,
            shutter_speed=res.md_shutter_speed,
            iso=res.md_iso,
            width=res.md_width,
            height=res.md_height,
            duration=res.md_duration,
            gps_lat=res.md_gps_lat,
            gps_lon=res.md_gps_lon,
            orientation=res.md_orientation,
        )

        _print_metadata(md)


def _print_metadata(md: Any) -> None:  # type: ignore[no-untyped-def]
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
