"""CLI-first movie/TV/music organizer commands."""

from __future__ import annotations

from pathlib import Path

import click

from mm.cli import ui
from mm.config import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, get_config
from mm.organizer.artwork import ArtworkPlan, download_artwork, plan_artwork
from mm.organizer.filename import ParsedMediaFile, parse_media_filename
from mm.organizer.nfo import NfoDocument, build_nfo, write_nfo
from mm.organizer.rename import RenamePlan, apply_rename_plan, plan_renames
from mm.organizer.scrapers import ScrapeCandidate, ScrapeQuery, configured_source_rows, search_all


@click.group("media")
def media() -> None:
    """Movie/TV/music organizer tools."""


@media.command("sources")
def sources() -> None:
    """List configured scraper sources and credential status."""
    ui.print_table(
        [
            ui.Column("Source"),
            ui.Column("Enabled"),
            ui.Column("Implemented"),
            ui.Column("Credentials"),
            ui.Column("Base URL", max_width=60),
        ],
        configured_source_rows(),
        title="Scraper Sources",
    )


@media.command("identify")
@click.argument("paths", nargs=-1, required=True, type=click.Path(path_type=Path))
@click.option("-r", "--recursive", is_flag=True, help="Recursively scan directories.")
def identify(paths: tuple[Path, ...], recursive: bool) -> None:
    """Parse filenames as movie, TV episode, album, or track candidates."""
    parsed = _parse_paths(paths, recursive=recursive)
    if not parsed:
        ui.warning("No media files could be identified.")
        return
    _print_identified(parsed)


@media.command("scrape")
@click.argument("paths", nargs=-1, required=True, type=click.Path(path_type=Path))
@click.option("-r", "--recursive", is_flag=True, help="Recursively scan directories.")
@click.option("--source", help="Use one scraper source, e.g. tmdb or omdb.")
@click.option("--limit", default=3, show_default=True, type=click.IntRange(1, 20))
def scrape(paths: tuple[Path, ...], recursive: bool, source: str | None, limit: int) -> None:
    """Search scraper sources for parsed movie/TV/music files."""
    parsed = _parse_paths(paths, recursive=recursive)
    if not parsed:
        ui.warning("No media files could be identified.")
        return

    rows: list[list[object]] = []
    for item in parsed:
        query = ScrapeQuery(
            media_type=item.media_type,
            title=item.title,
            artist=item.artist,
            album=item.album,
            year=item.year,
            season=item.season,
            episode=item.episode,
            track=item.track,
        )
        candidates = search_all(query, source=source, limit=limit)
        if not candidates:
            rows.append([item.path.name, item.media_type, item.title, "-", "-", "-", "-"])
            continue
        best = candidates[0]
        rows.append([
            item.path.name,
            item.media_type,
            item.title,
            best.source,
            f"{best.title}{f' ({best.year})' if best.year else ''}",
            best.artist or best.album or "",
            f"{best.confidence:.2f}",
        ])

    ui.print_table(
        [
            ui.Column("File", max_width=42),
            ui.Column("Type"),
            ui.Column("Parsed title", max_width=32),
            ui.Column("Source"),
            ui.Column("Best match", max_width=42),
            ui.Column("Artist/Album", max_width=32),
            ui.Column("Score", justify="right"),
        ],
        rows,
        title="Scrape Candidates",
    )


@media.command("search")
@click.argument("query")
@click.option(
    "--type",
    "media_type",
    type=click.Choice(["movie", "tv", "album", "track"]),
    default="movie",
)
@click.option("--year", type=int)
@click.option("--artist")
@click.option("--album")
@click.option("--source", help="Use one scraper source, e.g. tmdb or omdb.")
@click.option("--limit", default=5, show_default=True, type=click.IntRange(1, 20))
def search(
    query: str,
    media_type: str,
    year: int | None,
    artist: str | None,
    album: str | None,
    source: str | None,
    limit: int,
) -> None:
    """Search configured scraper sources directly."""
    candidates = search_all(
        ScrapeQuery(media_type=media_type, title=query, artist=artist, album=album, year=year),
        source=source,
        limit=limit,
    )
    if not candidates:
        ui.warning(
            "No candidates found. Check credentials with `mm media sources` and set them with "
            "`mm config --global scrapers.sources.tmdb.credentials.api_key ...`.",
        )
        return
    ui.print_table(
        [
            ui.Column("Source"),
            ui.Column("ID"),
            ui.Column("Type"),
            ui.Column("Title", max_width=48),
            ui.Column("Artist", max_width=32),
            ui.Column("Album", max_width=32),
            ui.Column("Year", justify="right"),
            ui.Column("Score", justify="right"),
        ],
        [
            [
                c.source,
                c.source_id,
                c.media_type,
                c.title,
                c.artist,
                c.album,
                c.year or "",
                f"{c.confidence:.2f}",
            ]
            for c in candidates
        ],
        title="Search Results",
    )


@media.command("rename")
@click.argument("paths", nargs=-1, required=True, type=click.Path(path_type=Path))
@click.option("-r", "--recursive", is_flag=True, help="Recursively scan directories.")
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Destination root.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without writing. This is the default.",
)
@click.option("--apply", "apply_changes", is_flag=True, help="Apply changes. Default is dry-run.")
def rename(
    paths: tuple[Path, ...],
    recursive: bool,
    output: Path | None,
    dry_run: bool,
    apply_changes: bool,
) -> None:
    """Plan or apply safe file renames using organizer templates."""
    _check_dry_run_apply(dry_run, apply_changes)
    parsed = _parse_paths(paths, recursive=recursive)
    if not parsed:
        ui.warning("No media files could be identified.")
        return
    root = _destination_root(paths, output)
    plan = plan_renames(parsed, root=root, templates=get_config().organizer.templates)
    _print_rename_plan(plan)
    if plan.conflicts:
        ui.error("Rename plan has conflicts; nothing was changed.")
        raise SystemExit(1)
    if not apply_changes:
        ui.info("Dry-run only. Re-run with `--apply` to move files.")
        return
    count = apply_rename_plan(plan)
    ui.success(f"Renamed {count} file(s)")


@media.command("nfo")
@click.argument("paths", nargs=-1, required=True, type=click.Path(path_type=Path))
@click.option("-r", "--recursive", is_flag=True, help="Recursively scan directories.")
@click.option("--source", help="Use one scraper source for best-match metadata.")
@click.option("--scrape", "use_scrape", is_flag=True, help="Use scraper metadata in NFO output.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without writing. This is the default.",
)
@click.option("--apply", "apply_changes", is_flag=True, help="Write files. Default is dry-run.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing NFO files.")
def nfo(
    paths: tuple[Path, ...],
    recursive: bool,
    source: str | None,
    use_scrape: bool,
    dry_run: bool,
    apply_changes: bool,
    overwrite: bool,
) -> None:
    """Plan or write minimal Kodi/Jellyfin-compatible NFO files."""
    _check_dry_run_apply(dry_run, apply_changes)
    parsed = _parse_paths(paths, recursive=recursive)
    if not parsed:
        ui.warning("No media files could be identified.")
        return
    documents = [
        _build_nfo_with_best_match(item, source=source) if use_scrape else build_nfo(item)
        for item in parsed
    ]
    _print_nfo_plan(documents)
    if not apply_changes:
        ui.info("Dry-run only. Re-run with `--apply` to write NFO files.")
        return
    written = 0
    for document in documents:
        try:
            write_nfo(document, overwrite=overwrite)
            written += 1
        except FileExistsError:
            ui.warning(f"Skip existing NFO: {document.target}", stderr=True)
    ui.success(f"Wrote {written} NFO file(s)")


@media.command("artwork")
@click.argument("paths", nargs=-1, required=True, type=click.Path(path_type=Path))
@click.option("-r", "--recursive", is_flag=True, help="Recursively scan directories.")
@click.option("--source", help="Use one scraper source for artwork.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without downloading. This is the default.",
)
@click.option("--apply", "apply_changes", is_flag=True, help="Download files. Default is dry-run.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing artwork.")
def artwork(
    paths: tuple[Path, ...],
    recursive: bool,
    source: str | None,
    dry_run: bool,
    apply_changes: bool,
    overwrite: bool,
) -> None:
    """Plan or download poster/folder artwork from scraper candidates."""
    _check_dry_run_apply(dry_run, apply_changes)
    parsed = _parse_paths(paths, recursive=recursive)
    if not parsed:
        ui.warning("No media files could be identified.")
        return
    plans = [_build_artwork_plan(item, source=source, overwrite=overwrite) for item in parsed]
    _print_artwork_plan(plans)
    if not apply_changes:
        ui.info("Dry-run only. Re-run with `--apply` to download artwork.")
        return
    downloaded = 0
    for plan in plans:
        if plan.status != "ready":
            continue
        download_artwork(plan, timeout=get_config().scrapers.timeout)
        downloaded += 1
    ui.success(f"Downloaded {downloaded} artwork file(s)")


def _iter_media_files(path: Path, *, recursive: bool) -> list[Path]:
    extensions = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
    if path.is_file():
        return [path] if path.suffix.lower() in extensions else []
    if not path.is_dir():
        return []
    pattern = "**/*" if recursive else "*"
    return [
        candidate
        for candidate in path.glob(pattern)
        if candidate.is_file() and candidate.suffix.lower() in extensions
    ]


def _parse_paths(paths: tuple[Path, ...], *, recursive: bool) -> list[ParsedMediaFile]:
    parsed: list[ParsedMediaFile] = []
    for path in paths:
        for candidate in _iter_media_files(path, recursive=recursive):
            item = parse_media_filename(candidate)
            if item:
                parsed.append(item)
    return parsed


def _check_dry_run_apply(dry_run: bool, apply_changes: bool) -> None:
    if dry_run and apply_changes:
        ui.error("Use either --dry-run or --apply, not both.")
        raise SystemExit(1)


def _destination_root(paths: tuple[Path, ...], output: Path | None) -> Path:
    if output:
        return output
    if len(paths) == 1 and paths[0].is_dir():
        return paths[0]
    files = [path for path in paths if path.is_file()]
    if files:
        return files[0].resolve().parent
    return Path.cwd()


def _query_for(item: ParsedMediaFile) -> ScrapeQuery:
    return ScrapeQuery(
        media_type=item.media_type,
        title=item.title,
        artist=item.artist,
        album=item.album,
        year=item.year,
        season=item.season,
        episode=item.episode,
        track=item.track,
    )


def _best_match(item: ParsedMediaFile, source: str | None = None) -> ScrapeCandidate | None:
    candidates = search_all(_query_for(item), source=source, limit=1)
    return candidates[0] if candidates else None


def _build_nfo_with_best_match(item: ParsedMediaFile, source: str | None) -> NfoDocument:
    return build_nfo(item, _best_match(item, source=source))


def _build_artwork_plan(
    item: ParsedMediaFile,
    *,
    source: str | None,
    overwrite: bool,
) -> ArtworkPlan:
    return plan_artwork(item, _best_match(item, source=source), overwrite=overwrite)


def _print_identified(items: list[ParsedMediaFile]) -> None:
    ui.print_table(
        [
            ui.Column("File", max_width=48),
            ui.Column("Type"),
            ui.Column("Title", max_width=36),
            ui.Column("Artist", max_width=26),
            ui.Column("Album", max_width=26),
            ui.Column("Year", justify="right"),
            ui.Column("S", justify="right"),
            ui.Column("E", justify="right"),
            ui.Column("Track", justify="right"),
            ui.Column("Score", justify="right"),
        ],
        [
            [
                item.path.name,
                item.media_type,
                item.title,
                item.artist or "",
                item.album or "",
                item.year or "",
                item.season or "",
                item.episode or "",
                item.track or "",
                f"{item.confidence:.2f}",
            ]
            for item in items
        ],
        title="Identified Media",
    )


def _print_rename_plan(plan: RenamePlan) -> None:
    ui.print_table(
        [
            ui.Column("Status"),
            ui.Column("Type"),
            ui.Column("Source", max_width=44),
            ui.Column("Target", max_width=56),
            ui.Column("Reason", max_width=32),
        ],
        [
            _rename_plan_row(plan, op)
            for op in plan.operations
        ],
        title="Rename Plan",
    )


def _rename_plan_row(plan: RenamePlan, op) -> list[object]:
    target = op.target.relative_to(plan.root) if op.target.is_relative_to(plan.root) else op.target
    return [
        op.status,
        op.media_type,
        op.source.name,
        str(target),
        op.reason,
    ]


def _print_nfo_plan(documents: list[NfoDocument]) -> None:
    ui.print_table(
        [
            ui.Column("Type"),
            ui.Column("Target", max_width=72),
        ],
        [[doc.media_type, str(doc.target)] for doc in documents],
        title="NFO Plan",
    )


def _print_artwork_plan(plans: list[ArtworkPlan]) -> None:
    ui.print_table(
        [
            ui.Column("Status"),
            ui.Column("Type"),
            ui.Column("Target", max_width=64),
            ui.Column("Reason", max_width=36),
        ],
        [[plan.status, plan.media_type, str(plan.target), plan.reason] for plan in plans],
        title="Artwork Plan",
    )
