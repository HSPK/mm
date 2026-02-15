"""uom info — show metadata for a single file."""

from __future__ import annotations

from pathlib import Path

import click

from uom.cli import Context, pass_ctx


@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--raw", is_flag=True, help="Always extract from file (ignore database).")
@pass_ctx
def info(ctx: Context, file: Path, raw: bool) -> None:
    """Show metadata for a single media file."""
    resolved = str(file.resolve())

    # Try database first (unless --raw)
    if not raw:
        repo = ctx.repo
        media = repo.get_media_by_path(resolved)
        if media and media.id is not None:
            md = repo.get_metadata(media.id)
            tags_info = repo.tags_for_media(media.id)

            click.echo(f"File     : {media.path}")
            click.echo(f"Type     : {media.media_type.value}")
            click.echo(f"Size     : {_fmt_size(media.file_size)}")
            click.echo(f"Hash     : {media.file_hash or '(not computed)'}")
            click.echo(f"Scanned  : {media.scanned_at}")
            click.echo()

            if md:
                _print_metadata(md)
            else:
                click.echo("(no metadata in database)")

            if tags_info:
                click.echo()
                click.echo("Tags:")
                for t, conf in tags_info:
                    conf_str = f" ({conf:.2f})" if conf < 1.0 else ""
                    click.echo(f"  {t.name}{conf_str}  [{t.source.value}]")
            return

    # Fallback: extract directly from file
    click.echo(f"File     : {resolved}")
    click.echo(f"Size     : {_fmt_size(file.stat().st_size)}")
    click.echo()

    from uom.core.metadata import check_tools, extract_metadata

    missing = check_tools()
    if missing:
        click.secho(
            f"Warning: {', '.join(missing)} not found — metadata may be incomplete."
            " Install via: brew install exiftool ffmpeg",
            fg="yellow",
            err=True,
        )

    md = extract_metadata(file, media_id=0)
    _print_metadata(md)


def _print_metadata(md) -> None:  # type: ignore[no-untyped-def]
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


def _fmt_size(n: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"
