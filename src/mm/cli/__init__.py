from __future__ import annotations

import click

from mm import __version__
from mm.cli import ui


def active_library():  # noqa: ANN201
    """Return the active library context, or exit with an error."""
    from mm.library.context import NoActiveDatabaseError, load_active_library

    try:
        return load_active_library()
    except NoActiveDatabaseError:
        ui.error("No active database. Run `mm init <directory>` to create one.")
        raise SystemExit(1)


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
    from mm.cli.geo import geo  # noqa: F811
    from mm.cli.importer import import_cmd  # noqa: F811
    from mm.cli.info import info  # noqa: F811
    from mm.cli.init import init  # noqa: F811
    from mm.cli.search import search  # noqa: F811
    from mm.cli.server import server  # noqa: F811

    cli.add_command(init)
    cli.add_command(config)
    cli.add_command(search)
    cli.add_command(import_cmd, "import")
    cli.add_command(info)
    cli.add_command(server)
    cli.add_command(db)
    cli.add_command(geo)


_register()
