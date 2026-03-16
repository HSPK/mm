from __future__ import annotations

import os

import click


@click.command()
@click.option("-p", "--port", type=int, default=8000, show_default=True, help="Port to listen on.")
@click.option("-h", "--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development.")
def server(port: int, host: str, do_reload: bool) -> None:
    """Start the MM web UI server."""
    import uvicorn

    from mm.config import get_active_db

    active = get_active_db()
    if not active or not active.exists():
        click.secho(
            "No active database. Run `mm init <directory>` first.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    db_path = active
    lib_dir = db_path.parent

    click.echo(f"Starting MM server at http://{host}:{port}")
    click.echo(f"Library : {lib_dir}")
    click.echo(f"Database: {db_path}")
    click.echo("Press Ctrl+C to stop.\n")

    os.environ["MM_DB"] = str(db_path)

    uvicorn.run(
        "mm.server.app:app",
        host=host,
        port=port,
        reload=do_reload,
        log_level="info",
    )
