"""uom server — start the web UI."""

from __future__ import annotations

import click

from uom.cli import Context, pass_ctx


@click.command()
@click.option("-p", "--port", type=int, default=8000, show_default=True, help="Port to listen on.")
@click.option("-h", "--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development.")
@pass_ctx
def server(ctx: Context, port: int, host: str, do_reload: bool) -> None:
    """Start the UOM web UI server."""
    import uvicorn

    click.echo(f"Starting UOM server at http://{host}:{port}")
    click.echo(f"Database: {ctx.db_path.resolve()}")
    click.echo("Press Ctrl+C to stop.\n")

    # Pass db_path via environment so the ASGI factory can pick it up
    import os

    os.environ["UOM_DB"] = str(ctx.db_path)

    uvicorn.run(
        "uom.server.app:app",
        host=host,
        port=port,
        reload=do_reload,
        log_level="info",
    )
