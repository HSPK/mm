from __future__ import annotations

from pathlib import Path

import click

from mm import __version__
from mm.config import DEFAULT_DB_NAME, DEFAULT_IMPORT_TEMPLATE, add_database, get_active_db

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
# mm init
# ---------------------------------------------------------------------------


@cli.command()
@click.argument(
    "directory",
    type=click.Path(path_type=Path),
    default=None,
    required=False,
)
def init(directory: Path | None) -> None:
    """Create (or open) a media library.

    Interactively asks for the library directory, name, and import template.
    Initialises a new database and registers it in ~/.config/mm.yaml.
    """
    if directory is None:
        directory = Path(click.prompt("Library directory", default=".", type=str))

    dest = directory.resolve()
    name = click.prompt("Library name", default=dest.name)
    template = click.prompt("Import template", default=DEFAULT_IMPORT_TEMPLATE)
    lib_root = Path(
        click.prompt("Library root (where media files are stored)", default=str(dest))
    ).resolve()

    dest.mkdir(parents=True, exist_ok=True)
    db_path = dest / DEFAULT_DB_NAME

    # Create / upgrade the database
    from mm.db.sync_repo import SyncRepo

    repo = SyncRepo(db_path)

    # Store config in DB
    repo.set_config("import_template", template)
    repo.set_config("library_name", name)
    repo.set_config("library_root", str(lib_root))

    # Seed default user and smart albums
    if repo.count_users() == 0:
        admin_name = click.prompt("Admin username", default="admin")
        admin_pass = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
        repo.create_user(admin_name, password=admin_pass, display_name=admin_name, is_admin=True)
        click.echo(f"Created admin user: {admin_name}")
    if click.confirm("Seed default smart albums?", default=True):
        repo.seed_smart_albums()

    click.echo(f"Database ready: {db_path}")

    idx = add_database(db_path, name=name)
    # Ensure it's the active one
    from mm.config import set_active_database

    set_active_database(idx)
    click.echo(f"Active library: {dest}  (#{idx + 1})")


# ---------------------------------------------------------------------------
# Import and register sub-commands
# ---------------------------------------------------------------------------


def _register() -> None:
    from mm.cli.db import db  # noqa: F811
    from mm.cli.dedup import dedup  # noqa: F811
    from mm.cli.geo import geo  # noqa: F811
    from mm.cli.importer import import_cmd  # noqa: F811
    from mm.cli.info import info  # noqa: F811
    from mm.cli.search import search  # noqa: F811
    from mm.cli.server import server  # noqa: F811

    cli.add_command(search)
    cli.add_command(dedup)
    cli.add_command(import_cmd, "import")
    cli.add_command(info)
    cli.add_command(server)
    cli.add_command(db)
    cli.add_command(geo)


_register()
