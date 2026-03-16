from __future__ import annotations

from pathlib import Path

import click

from mm.config import (
    add_database,
    load_config,
    remove_database,
    set_active_database,
)


@click.group(invoke_without_command=True)
@click.pass_context
def db(ctx: click.Context) -> None:
    """Database management."""
    if ctx.invoked_subcommand is None:
        from mm.config import get_active_db

        db_path = get_active_db()
        if db_path:
            click.echo(f"Active database: {db_path}")
        else:
            click.echo("No active database. Run `mm init <directory>` first.")


# ---------------------------------------------------------------------------
# db list / add / set
# ---------------------------------------------------------------------------


@db.command("list")
def db_list() -> None:
    """List all registered databases."""
    cfg = load_config()
    dbs = cfg.get("databases", [])
    active = cfg.get("active", -1)

    if not dbs:
        click.echo("No databases registered. Run `mm init <directory>` to create one.")
        return

    for i, entry in enumerate(dbs):
        marker = "*" if i == active else " "
        name = entry.get("name", "")
        path = entry["path"]
        label = f"  {marker} {i + 1}. {path}"
        if name:
            label += f"  ({name})"
        exists = Path(path).exists()
        if not exists:
            label += "  [missing]"
        click.echo(label)


@db.command("add")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--name", default=None, help="A friendly name for this library.")
def db_add(path: Path, name: str | None) -> None:
    """Register an existing database file."""
    resolved = path.resolve()
    if resolved.is_dir():
        from mm.config import DEFAULT_DB_NAME

        resolved = resolved / DEFAULT_DB_NAME
    if not resolved.exists():
        click.secho(f"File not found: {resolved}", fg="red", err=True)
        raise SystemExit(1)
    idx = add_database(resolved, name=name)
    click.echo(f"Added database #{idx + 1}: {resolved}")


@db.command("set")
@click.argument("number", type=int)
def db_set(number: int) -> None:
    """Set the active database by its number (from `db list`)."""
    try:
        path = set_active_database(number - 1)  # user sees 1-based
        click.echo(f"Active database set to #{number}: {path}")
    except ValueError as e:
        click.secho(str(e), fg="red", err=True)
        raise SystemExit(1)


@db.command("rm")
@click.argument("number", type=int)
@click.option("--delete-data", is_flag=True, help="Also delete the database file from disk.")
def db_rm(number: int, delete_data: bool) -> None:
    """Remove a database from the config by its number (from `db list`).

    By default only unregisters the database.  Use --delete-data to also
    delete the .db file from disk.
    """
    try:
        removed = remove_database(number - 1)
    except ValueError as e:
        click.secho(str(e), fg="red", err=True)
        raise SystemExit(1)

    click.echo(f"Removed #{number}: {removed}")

    if delete_data and removed.exists():
        if click.confirm(f"Delete {removed} from disk?"):
            removed.unlink()
            click.echo("Database file deleted.")
        else:
            click.echo("File kept on disk.")


# ---------------------------------------------------------------------------
# Register remaining subcommands (stats, clean, export, sync, migrate-paths)
# ---------------------------------------------------------------------------


def _register() -> None:
    from mm.cli.db.clean import db_clean
    from mm.cli.db.stats import db_stats
    from mm.cli.db.sync import db_sync

    db.add_command(db_stats)
    db.add_command(db_clean)
    db.add_command(db_sync)


_register()
