"""mm config — get/set active library or global config values."""

from __future__ import annotations

import click
import yaml

from mm.cli import ui


@click.command("config")
@click.option(
    "--global",
    "global_config",
    is_flag=True,
    help="Read/write ~/.config/mm.yaml instead of the active library config.",
)
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(global_config: bool, key: str | None, value: str | None) -> None:
    """Get or set active library config values.

    \b
    Examples:
      mm config                       # list all config
      mm config import_template       # get a value
      mm config import_template "{year}/{month:02d}/{day:02d}/{type}{ext}"
      mm config --global scrapers.sources.tmdb.credentials.api_key "..."
    """
    if global_config:
        handle_global_config(key, value)
        return

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


def handle_global_config(key: str | None, value: str | None) -> None:
    from mm.config import CliConfig, load_cli_config, save_cli_config

    current = load_cli_config()
    values = current.model_dump(mode="json", by_alias=True)

    if key is None:
        rows = [[k, _mask_secrets(v)] for k, v in sorted(values.items())]
        ui.print_table(
            [ui.Column("Key"), ui.Column("Value", max_width=96)],
            rows,
            title="Global Config",
        )
        return

    if value is None:
        try:
            ui.plain(_mask_secrets(_get_path(values, key)))
        except KeyError:
            ui.warning(f"Key not found: {key}", stderr=True)
            raise SystemExit(1)
        return

    parsed = _parse_value(value)
    next_values = _set_path(values, key, parsed)
    try:
        new_config = CliConfig.model_validate(next_values)
    except ValueError as err:
        ui.error(err)
        raise SystemExit(1)
    save_cli_config(new_config)
    ui.success(f"{key} = {_mask_secrets(parsed)}")


def _parse_value(value: str) -> object:
    parsed = yaml.safe_load(value)
    return value if parsed is None and value.strip().lower() != "null" else parsed


def _get_path(data: object, dotted_key: str) -> object:
    current = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_key)
        current = current[part]
    return current


def _set_path(data: dict[str, object], dotted_key: str, value: object) -> dict[str, object]:
    parts = dotted_key.split(".")
    if not parts or any(not part for part in parts):
        raise KeyError(dotted_key)
    root = dict(data)
    current: dict[str, object] = root
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
        if not isinstance(child, dict):
            raise KeyError(dotted_key)
        next_child = dict(child)
        current[part] = next_child
        current = next_child
    current[parts[-1]] = value
    return root


def _mask_secrets(value: object) -> object:
    if isinstance(value, dict):
        masked: dict[str, object] = {}
        for key, item in value.items():
            lower = key.lower()
            if any(token in lower for token in ("key", "token", "secret", "password", "pin")):
                masked[key] = "******" if item else ""
            else:
                masked[key] = _mask_secrets(item)
        return masked
    if isinstance(value, list):
        return [_mask_secrets(item) for item in value]
    return value
