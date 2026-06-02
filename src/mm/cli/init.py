"""mm init — create or open a media library."""

from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui
from mm.config import DEFAULT_IMPORT_TEMPLATE


@click.command()
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

    from mm.library.setup import initialize_library, inspect_library_setup

    requirements = inspect_library_setup(dest)
    admin_name = None
    admin_pass = None
    if requirements.needs_admin_user:
        admin_name = click.prompt("Admin username", default="admin")
        admin_pass = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)

    seed_smart_albums = ui.confirm("Seed default smart albums?", default=True)
    result = initialize_library(
        destination=dest,
        name=name,
        import_template=template,
        library_root=lib_root,
        admin_username=admin_name,
        admin_password=admin_pass,
        seed_smart_albums=seed_smart_albums,
    )
    if result.created_admin_user:
        ui.success(f"Created admin user: {result.created_admin_user}")
    if result.seeded_smart_albums:
        ui.success(f"Seeded {result.seeded_smart_albums:,} default smart album definitions.")

    ui.success(f"Database ready: {result.db_path}")
    ui.key_values(
        "Active Library",
        [("Path", ui.path(dest)), ("Number", f"#{result.active_index + 1}")],
    )
