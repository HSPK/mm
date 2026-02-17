"""uom dedup — find and remove duplicate media files."""

from __future__ import annotations

from pathlib import Path

import click

from uom.cli import Context, pass_ctx
from uom.core.dedup import DedupStrategy


def _click_progress():
    """Return an on_progress callback that drives a click progressbar."""
    bar = None

    def _cb(current: int, total: int) -> None:
        nonlocal bar
        if bar is None:
            bar = click.progressbar(length=total, label="Hashing files")
            bar.__enter__()
        bar.update(1)
        if current >= total:
            bar.__exit__(None, None, None)

    return _cb


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["name", "hash"], case_sensitive=False),
    default="name",
    show_default=True,
    help="Dedup strategy: 'name' (same stem .jpg/.jpeg) or 'hash' (identical SHA-256).",
)
@click.option("--delete", is_flag=True, help="Actually delete duplicates (default: dry-run).")
@pass_ctx
def dedup(ctx: Context, directory: Path, strategy: str, delete: bool) -> None:
    """Find and remove duplicate media files."""
    from uom.core.dedup import find_duplicates

    strat = DedupStrategy(strategy)
    click.echo(f"Strategy: {strat.value}")
    click.echo(f"Scanning: {directory.resolve()}\n")

    pairs = find_duplicates(directory, strategy=strat, on_progress=_click_progress())

    if not pairs:
        click.echo("No duplicates found.")
        return

    total_saved = sum(p.remove.stat().st_size for p in pairs if p.remove.exists())
    click.echo(
        f"\nFound {len(pairs)} duplicate pair(s), can free {total_saved / 1024 / 1024:.1f} MB\n"
    )

    if delete:
        with click.progressbar(pairs, label="Deleting duplicates") as bar:
            for pair in bar:
                if pair.remove.exists():
                    pair.remove.unlink()
        click.echo(
            f"\nDone. Removed {len(pairs)} file(s), freed {total_saved / 1024 / 1024:.1f} MB."
        )
    else:
        for pair in pairs:
            click.echo(f"  KEEP   : {pair.keep}")
            click.echo(f"  REMOVE : {pair.remove}")
            click.echo()
        click.echo("Dry-run mode — no files deleted. Use --delete to remove them.")
