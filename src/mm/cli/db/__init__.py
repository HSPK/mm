from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui
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
            ui.key_values("Database", [("Active", ui.path(db_path))])
        else:
            ui.warning("No active database. Run `mm init <directory>` first.")


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
        ui.warning("No databases registered. Run `mm init <directory>` to create one.")
        return

    rows: list[list[object]] = []
    for i, entry in enumerate(dbs):
        name = entry.get("name", "")
        path = entry["path"]
        exists = Path(path).exists()
        rows.append(
            [
                "●" if i == active else "",
                str(i + 1),
                name or "-",
                ui.path(path),
                "ok" if exists else "missing",
            ]
        )
    ui.print_table(
        [
            ui.Column("Active", justify="center"),
            ui.Column("#", justify="right"),
            ui.Column("Name"),
            ui.Column("Path", max_width=72),
            ui.Column("Status"),
        ],
        rows,
        title="Registered Databases",
    )


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
        ui.error(f"File not found: {resolved}")
        raise SystemExit(1)
    idx = add_database(resolved, name=name)
    ui.success(f"Added database #{idx + 1}: {resolved}")


@db.command("set")
@click.argument("number", type=int)
def db_set(number: int) -> None:
    """Set the active database by its number (from `db list`)."""
    try:
        path = set_active_database(number - 1)  # user sees 1-based
        ui.success(f"Active database set to #{number}: {path}")
    except ValueError as e:
        ui.error(str(e))
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
        ui.error(str(e))
        raise SystemExit(1)

    ui.success(f"Removed #{number}: {removed}")

    if delete_data and removed.exists():
        if ui.confirm(f"Delete {removed} from disk?"):
            removed.unlink()
            ui.success("Database file deleted.")
        else:
            ui.info("File kept on disk.")


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
