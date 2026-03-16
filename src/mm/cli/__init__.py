from __future__ import annotations

from pathlib import Path

import click

from mm import __version__
from mm.config import get_active_db

# ---------------------------------------------------------------------------
# Helpers — any command that needs the DB calls these directly
# ---------------------------------------------------------------------------


def get_db_path() -> Path:
    """Return the active database path, or exit with an error."""
    db_path = get_active_db()
    if db_path is None or not db_path.exists():
        click.secho(
            "No active database. Run `mm init <directory>` to create one.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)
    return db_path


def get_repo():  # noqa: ANN201
    """Return a SyncRepo connected to the active database."""
    from mm.db.sync_repo import SyncRepo

    return SyncRepo(get_db_path())


def get_library_root() -> Path:
    """Return the library root directory from DB config, falling back to db parent."""
    repo = get_repo()
    stored = repo.get_config("library_root")
    if stored:
        return Path(stored)
    return get_db_path().parent


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="mm")
def cli() -> None:
    """MM — Lite Media Manager"""


# ---------------------------------------------------------------------------
# Import and register sub-commands
# ---------------------------------------------------------------------------


def _register() -> None:
    from mm.cli.config_cmd import config  # noqa: F811
    from mm.cli.db import db  # noqa: F811
    from mm.cli.dedup import dedup  # noqa: F811
    from mm.cli.geo import geo  # noqa: F811
    from mm.cli.importer import import_cmd  # noqa: F811
    from mm.cli.info import info  # noqa: F811
    from mm.cli.init import init  # noqa: F811
    from mm.cli.search import search  # noqa: F811
    from mm.cli.server import server  # noqa: F811

    cli.add_command(init)
    cli.add_command(config)
    cli.add_command(search)
    cli.add_command(dedup)
    cli.add_command(import_cmd, "import")
    cli.add_command(info)
    cli.add_command(server)
    cli.add_command(db)
    cli.add_command(geo)


_register()
