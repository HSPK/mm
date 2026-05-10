"""mm config — get/set library config values."""

from __future__ import annotations

import click

from mm.cli import ui


@click.command("config")
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--unset", is_flag=True, help="Remove a config key.")
def config(key: str | None, value: str | None, unset: bool) -> None:
    """Get or set library config values.

    \b
    Examples:
      mm config                       # list all config
      mm config import_template       # get a value
      mm config import_template "{year}/{original_name}{ext}"  # set a value
      mm config --unset import_template  # remove a key
    """
    from mm.cli import get_repo

    repo = get_repo()

    if key is None:
        # List all config
        all_cfg = repo.get_all_config()
        if not all_cfg:
            ui.warning("No config values set.")
            return
        ui.print_table(
            [ui.Column("Key"), ui.Column("Value", max_width=96)],
            [[k, v] for k, v in sorted(all_cfg.items())],
            title="Config",
        )
        return

    if unset:
        repo.set_config(key, "")
        ui.success(f"Unset: {key}")
        return

    if value is None:
        # Get
        result = repo.get_config(key)
        if result:
            ui.plain(result)
        else:
            ui.warning(f"Key not found: {key}", stderr=True)
            raise SystemExit(1)
    else:
        # Set
        repo.set_config(key, value)
        ui.success(f"{key} = {value}")
