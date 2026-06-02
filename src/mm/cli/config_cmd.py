"""mm config — get/set active library config values."""

from __future__ import annotations

import click

from mm.cli import ui


@click.command("config")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(key: str | None, value: str | None) -> None:
    """Get or set active library config values.

    \b
    Examples:
      mm config                       # list all config
      mm config import_template       # get a value
      mm config import_template "{year}/{month:02d}/{day:02d}/{type}{ext}"
    """
    from mm.cli import active_library
    from mm.library.settings import LibraryConfig

    active = active_library()
    current = active.config
    values = current.model_dump(mode="json")

    if key is None:
        ui.print_table(
            [ui.Column("Key"), ui.Column("Value", max_width=96)],
            [[k, v] for k, v in sorted(values.items())],
            title="Config",
        )
        return

    if value is None:
        if key not in values:
            ui.warning(f"Key not found: {key}", stderr=True)
            raise SystemExit(1)
        ui.plain(values[key])
    else:
        if key not in values:
            ui.warning(f"Key not found: {key}", stderr=True)
            raise SystemExit(1)
        new_config = LibraryConfig.model_validate({**values, key: value})
        active.db.library_config.set(new_config)
        ui.success(f"{key} = {value}")
