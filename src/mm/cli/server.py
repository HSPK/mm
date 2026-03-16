"""uom server — start the web UI."""

from __future__ import annotations

import os
from pathlib import Path

import click

from uom.cli import Context, pass_ctx
from uom.config import DEFAULT_DB_NAME


@click.command()
@click.argument("directory", type=click.Path(path_type=Path), default=".")
@click.option("-p", "--port", type=int, default=8000, show_default=True, help="Port to listen on.")
@click.option("-h", "--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development.")
@pass_ctx
def server(ctx: Context, directory: Path, port: int, host: str, do_reload: bool) -> None:
    """Start the UOM web UI server.

    DIRECTORY is the library root folder (default: current directory).
    If no database exists there, you will be asked whether to create one.
    """
    import uvicorn

    lib_dir = directory.resolve()
    db_path = lib_dir / DEFAULT_DB_NAME

    # If the user explicitly passed --db at the top-level, honour it
    if ctx.db_path != Path(DEFAULT_DB_NAME):
        db_path = ctx.db_path.resolve()
        lib_dir = db_path.parent

    if not db_path.exists():
        click.echo(f"No database found at: {db_path}")
        if not click.confirm("Initialize a new library here?", default=True):
            raise SystemExit(0)
        # Create the directory if needed, then let the server init the DB
        lib_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"A new library will be created at {lib_dir}")

    click.echo(f"Starting UOM server at http://{host}:{port}")
    click.echo(f"Library : {lib_dir}")
    click.echo(f"Database: {db_path}")
    click.echo("Press Ctrl+C to stop.\n")

    os.environ["UOM_DB"] = str(db_path)

    uvicorn.run(
        "uom.server.app:app",
        host=host,
        port=port,
        reload=do_reload,
        log_level="info",
    )
