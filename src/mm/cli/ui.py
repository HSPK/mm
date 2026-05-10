"""Unified Rich-backed presentation helpers for CLI commands."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

import click
from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "accent": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "cyan",
        "muted": "dim",
        "key": "bold cyan",
        "value": "white",
        "path": "magenta",
        "number": "bold white",
        "section": "bold cyan",
        "panel.border": "cyan",
        "table.header": "bold cyan",
        "table.border": "bright_black",
        "progress.description": "cyan",
        "progress.spinner": "cyan",
        "progress.track": "bright_black",
        "progress.complete": "cyan",
        "progress.finished": "green",
        "progress.pulse": "cyan",
        "bar.complete": "green",
        "bar.empty": "bright_black",
    }
)

console = Console(theme=THEME, highlight=False)
err_console = Console(stderr=True, theme=THEME, highlight=False)

Justify = Literal["left", "center", "right", "full"]
Overflow = Literal["fold", "crop", "ellipsis", "ignore"]
T = TypeVar("T")


@dataclass(frozen=True)
class Column:
    """A consistently styled table column."""

    header: str
    justify: Justify = "left"
    style: str | None = None
    no_wrap: bool = False
    max_width: int | None = None
    overflow: Overflow = "fold"
    ratio: int | None = None


@dataclass
class ProgressHandle:
    """Small wrapper around a Rich progress task."""

    progress: Progress
    task_id: TaskID

    def advance(self, step: int = 1) -> None:
        self.progress.advance(self.task_id, step)

    def update(self, completed: int | None = None, total: int | None = None) -> None:
        self.progress.update(self.task_id, completed=completed, total=total)


def path(value: str | Path) -> Text:
    return Text(str(value), style="path")


def value_text(value: object, style: str | None = None) -> Text:
    return Text(str(value), style=style or "value")


def plain(message: object = "") -> None:
    console.print(str(message), markup=False)


def blank() -> None:
    console.print()


def section(title: str, subtitle: str | None = None) -> None:
    text = Text(title, style="section")
    if subtitle:
        text.append(f" · {subtitle}", style="muted")
    console.rule(text, style="table.border")


def success(message: object) -> None:
    _message("✓", message, "success")


def info(message: object) -> None:
    _message("•", message, "info")


def note(message: object) -> None:
    _message("·", message, "muted")


def warning(message: object, *, stderr: bool = False) -> None:
    _message("!", message, "warning", stderr=stderr)


def error(message: object) -> None:
    _message("✗", message, "error", stderr=True)


def _message(prefix: str, message: object, style: str, *, stderr: bool = False) -> None:
    target = err_console if stderr else console
    text = Text()
    text.append(prefix, style=style)
    text.append(" ")
    text.append(str(message), style=style)
    target.print(text)


def panel(
    renderable: RenderableType,
    *,
    title: str | None = None,
    border_style: str = "panel.border",
) -> None:
    console.print(
        Panel(
            renderable,
            title=title,
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def key_values(
    title: str,
    items: Sequence[tuple[str, object]],
    *,
    border_style: str = "panel.border",
) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="key", no_wrap=True)
    table.add_column(style="value")
    for key, value in items:
        table.add_row(Text(key, style="key"), _render_cell(value))
    panel(table, title=title, border_style=border_style)


def print_table(
    columns: Sequence[Column],
    rows: Iterable[Sequence[object]],
    *,
    title: str | None = None,
    caption: str | None = None,
    show_lines: bool = False,
) -> None:
    table = Table(
        title=title,
        caption=caption,
        box=box.ROUNDED,
        border_style="table.border",
        header_style="table.header",
        row_styles=("", "dim"),
        show_lines=show_lines,
        expand=False,
    )
    for column in columns:
        table.add_column(
            column.header,
            justify=column.justify,
            style=column.style or "",
            no_wrap=column.no_wrap,
            max_width=column.max_width,
            overflow=column.overflow,
            ratio=column.ratio,
        )
    for row in rows:
        table.add_row(*[_render_cell(cell) for cell in row])
    console.print(table)


def bullet_list(title: str, items: Sequence[object], *, limit: int | None = None) -> None:
    shown = items if limit is None else items[:limit]
    lines: list[Text] = []
    for item in shown:
        line = Text("• ", style="accent")
        line.append(str(item), style="path")
        lines.append(line)
    if limit is not None and len(items) > limit:
        line = Text("• ", style="accent")
        line.append(f"... and {len(items) - limit} more", style="muted")
        lines.append(line)
    panel(Group(*lines), title=title)


def ratio_bar(part: int, whole: int, width: int = 14) -> Text:
    if whole <= 0:
        return Text("━" * width, style="bar.empty")
    filled = max(0, min(width, round(part / whole * width)))
    text = Text()
    text.append("━" * filled, style="bar.complete")
    text.append("━" * (width - filled), style="bar.empty")
    return text


def percent(part: int, whole: int) -> str:
    if whole <= 0:
        return "-"
    return f"{part * 100 / whole:.1f}%"


def confirm(message: str, *, default: bool = False, abort: bool = False) -> bool:
    return click.confirm(click.style(message, fg="yellow"), default=default, abort=abort)


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(style="progress.spinner"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(
            bar_width=None,
            style="progress.track",
            complete_style="progress.complete",
            finished_style="progress.finished",
            pulse_style="progress.pulse",
        ),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


@contextmanager
def progress(description: str, total: int | None) -> Iterator[ProgressHandle]:
    progress_bar = make_progress()
    with progress_bar:
        task_id = progress_bar.add_task(description, total=total)
        yield ProgressHandle(progress_bar, task_id)


def track(items: Iterable[T], description: str, *, total: int | None = None) -> Iterator[T]:
    if total is None and hasattr(items, "__len__"):
        total = len(items)  # type: ignore[arg-type]
    with progress(description, total) as bar:
        for item in items:
            yield item
            bar.advance()


@contextmanager
def status(message: str) -> Iterator[None]:
    with console.status(message, spinner="dots", spinner_style="progress.spinner"):
        yield


def _render_cell(value: object) -> RenderableType:
    if isinstance(value, Text):
        return value
    if isinstance(value, (Table, Panel, Group)):
        return value
    return Text(str(value), style="value")
