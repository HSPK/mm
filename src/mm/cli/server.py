from __future__ import annotations

import click

from mm.cli import ui


@click.command()
@click.option("-p", "--port", type=int, default=8000, show_default=True, help="Port to listen on.")
@click.option("-h", "--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development.")
def server(port: int, host: str, do_reload: bool) -> None:
    """Start the MM web UI server."""
    import uvicorn

    from mm.server.runtime import prepare_server_runtime

    runtime = prepare_server_runtime()
    if runtime is None:
        ui.error("No active database. Run `mm init <directory>` first.")
        raise SystemExit(1)

    ui.key_values(
        "MM Server",
        [
            ("URL", f"http://{host}:{port}"),
            ("Library", ui.path(runtime.library_dir)),
            ("Database", ui.path(runtime.database)),
        ],
    )
    ui.info("Press Ctrl+C to stop.")
    ui.blank()

    uvicorn.run(
        "mm.server.app:app",
        host=host,
        port=port,
        reload=do_reload,
        log_level="info",
    )
