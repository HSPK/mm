from __future__ import annotations

import click

from mm.cli import ui


@click.command()
def dedup() -> None:
    """Find and remove duplicate media files (by hash in the database)."""
    from mm.cli import get_library_root, get_repo
    from mm.core.dedup import find_duplicates

    repo = get_repo()
    root = get_library_root()
    ui.info("Searching for duplicates in the database...")

    groups = find_duplicates(repo)

    if not groups:
        ui.success("No duplicates found.")
        return

    total_dups = sum(len(g.duplicates) for g in groups)
    total_saved = 0
    for g in groups:
        for p in g.duplicates:
            try:
                total_saved += (root / p.path).stat().st_size
            except OSError:
                pass

    ui.key_values(
        "Duplicate Summary",
        [
            ("Duplicate files", f"{total_dups:,}"),
            ("Duplicate groups", f"{len(groups):,}"),
            ("Recoverable space", f"{total_saved / 1024 / 1024:.1f} MB"),
        ],
    )

    rows: list[list[object]] = []
    for g in groups:
        rows.append([g.file_hash[:12], "KEEP", ui.path(g.keep.path)])
        for dup in g.duplicates:
            rows.append([g.file_hash[:12], "REMOVE", ui.path(dup.path)])
    ui.print_table(
        [ui.Column("Hash"), ui.Column("Action"), ui.Column("Path", max_width=88)],
        rows,
        title="Duplicate Plan",
    )

    if ui.confirm("Delete these duplicates?"):
        deleted = 0
        for g in groups:
            for dup in g.duplicates:
                try:
                    repo.delete_media(dup.id)
                    if (root / dup.path).exists():
                        (root / dup.path).unlink(missing_ok=True)
                        deleted += 1
                except OSError as e:
                    ui.error(f"Error deleting {dup}: {e}")
        ui.success(f"Removed {deleted:,} file(s), freed {total_saved / 1024 / 1024:.1f} MB.")
    else:
        ui.warning("Aborted — no files deleted.")
