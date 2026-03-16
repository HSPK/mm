"""UOM CLI — top-level Click group and sub-command registration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click
from uom import __version__

from mm.config import DEFAULT_DB_NAME

if TYPE_CHECKING:
    from mm.db.sync_repo import SyncRepo

# ---------------------------------------------------------------------------
# Shared context / pass-decorator
# ---------------------------------------------------------------------------


class Context:
    """Shared state threaded through all sub-commands."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._repo = None

    @property
    def repo(self) -> SyncRepo:
        if self._repo is None:
            from mm.db.sync_repo import SyncRepo as _SyncRepo

            self._repo = _SyncRepo(self.db_path)
        return self._repo


pass_ctx = click.make_pass_decorator(Context, ensure=True)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="uom")
@click.option(
    "--db",
    type=click.Path(path_type=Path),
    default=DEFAULT_DB_NAME,
    envvar="UOM_DB",
    help="Path to the SQLite database file.",
)
@click.pass_context
def cli(ctx: click.Context, db: Path) -> None:
    """UOM — command-line media library manager."""
    ctx.obj = Context(db_path=db)


# ---------------------------------------------------------------------------
# Import and register sub-commands
# ---------------------------------------------------------------------------


def _register() -> None:
    from mm.cli.db import db  # noqa: F811
    from mm.cli.dedup import dedup  # noqa: F811
    from mm.cli.geo import geo  # noqa: F811
    from mm.cli.import_cmd import import_cmd  # noqa: F811
    from mm.cli.info import info  # noqa: F811
    from mm.cli.scan import scan  # noqa: F811
    from mm.cli.search import search  # noqa: F811
    from mm.cli.server import server  # noqa: F811
    from mm.cli.tag import tag  # noqa: F811

    cli.add_command(scan)
    cli.add_command(search)
    cli.add_command(dedup)
    cli.add_command(tag)
    cli.add_command(import_cmd, "import")
    cli.add_command(info)
    cli.add_command(server)
    cli.add_command(db)
    cli.add_command(geo)


_register()
