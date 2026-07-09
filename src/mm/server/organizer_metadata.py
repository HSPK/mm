from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from mm.config import load_cli_config


@dataclass(frozen=True)
class LocalMetadata:
    exists: bool = False
    title: str | None = None
    original_title: str | None = None
    show_title: str | None = None
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    premiered: str | None = None
    certification: str | None = None
    runtime: int | None = None
    genres: list[str] | None = None
    styles: list[str] | None = None
    composers: list[str] | None = None
    status: str | None = None
    countries: list[str] | None = None
    tagline: str | None = None
    plot: str | None = None
    lyrics: str | None = None
    synced_lyrics: str | None = None
    tags: list[str] | None = None
    ids: dict[str, str] | None = None
    rating: float | None = None
    rating_source: str | None = None
    studios: list[str] | None = None
    cast: list[str] | None = None


@dataclass
class OrganizerScanContext:
    children: dict[Path, list[Path]]
    artwork_files: dict[Path, list[Path]]
    metadata: dict[Path, LocalMetadata]
    image_sizes: dict[Path, tuple[int | None, int | None]]
    chinese_script: str

    @classmethod
    def create(cls) -> OrganizerScanContext:
        return cls(
            children={},
            artwork_files={},
            metadata={},
            image_sizes={},
            chinese_script=load_cli_config().organizer.chinese_script,
        )

    def list_children(self, directory: Path) -> list[Path]:
        key = directory.expanduser().resolve()
        if key not in self.children:
            self.children[key] = (
                sorted(directory.iterdir(), key=lambda item: item.name.lower())
                if directory.is_dir()
                else []
            )
        return self.children[key]



def _read_local_metadata(
    path: Path,
    media_type: str,
    context: OrganizerScanContext | None = None,
) -> LocalMetadata:
    if media_type == "tv":
        return _read_tv_metadata(path, context)
    if media_type == "track":
        return _read_track_metadata(path, context)
    for metadata_path in _metadata_paths(path, media_type, context):
        metadata = _read_metadata_file(metadata_path, context)
        if metadata.exists:
            return metadata
    return LocalMetadata()


def _has_metadata(path: Path, media_type: str) -> bool:
    if media_type == "track":
        return path.with_suffix(".nfo").is_file() or (path.parent / "album.nfo").is_file()
    if media_type == "tv":
        return (
            path.with_suffix(".nfo").is_file()
            or (path.parent / "tvshow.nfo").is_file()
            or (path.parent.parent / "tvshow.nfo").is_file()
        )
    return path.with_suffix(".nfo").is_file() or (path.parent / "movie.nfo").is_file()


def _read_track_metadata(path: Path, context: OrganizerScanContext | None = None) -> LocalMetadata:
    track = _read_metadata_file(path.with_suffix(".nfo"), context)
    album = _read_metadata_file(path.parent / "album.nfo", context)
    if not track.exists:
        return _album_metadata_for_track(album)
    if not album.exists:
        return track
    return LocalMetadata(
        exists=True,
        title=track.title,
        original_title=track.original_title,
        show_title=track.show_title,
        artist=track.artist or album.artist,
        album=album.title or album.album or track.album,
        year=album.year or track.year,
        premiered=track.premiered or album.premiered,
        certification=track.certification or album.certification,
        runtime=track.runtime,
        genres=track.genres or album.genres,
        styles=album.styles or track.styles,
        composers=track.composers or album.composers,
        status=track.status or album.status,
        countries=track.countries or album.countries,
        tagline=track.tagline or album.tagline,
        plot=track.plot or album.plot,
        lyrics=track.lyrics,
        synced_lyrics=track.synced_lyrics,
        tags=track.tags or album.tags,
        ids={**(album.ids or {}), **(track.ids or {})},
        rating=track.rating if track.rating is not None else album.rating,
        rating_source=track.rating_source or album.rating_source,
        studios=track.studios or album.studios,
        cast=track.cast or album.cast,
    )


def _album_metadata_for_track(album: LocalMetadata) -> LocalMetadata:
    if not album.exists:
        return album
    return LocalMetadata(
        exists=True,
        title=album.title,
        original_title=album.original_title,
        show_title=album.show_title,
        artist=album.artist,
        album=album.album or album.title,
        year=album.year,
        premiered=album.premiered,
        certification=album.certification,
        runtime=album.runtime,
        genres=album.genres,
        styles=album.styles,
        composers=album.composers,
        status=album.status,
        countries=album.countries,
        tagline=album.tagline,
        plot=album.plot,
        lyrics=album.lyrics,
        synced_lyrics=album.synced_lyrics,
        tags=album.tags,
        ids=album.ids,
        rating=album.rating,
        rating_source=album.rating_source,
        studios=album.studios,
        cast=album.cast,
    )


def _read_tv_metadata(path: Path, context: OrganizerScanContext | None = None) -> LocalMetadata:
    episode = _read_metadata_file(path.with_suffix(".nfo"), context)
    show = _first_metadata(
        [
            path.parent.parent / "tvshow.nfo",
            path.parent / "tvshow.nfo",
        ],
        context,
    )
    if not episode.exists:
        return show
    if not show.exists:
        return episode
    return LocalMetadata(
        exists=True,
        title=episode.title,
        original_title=episode.original_title or show.original_title,
        show_title=episode.show_title or show.show_title or show.title,
        year=episode.year or show.year,
        premiered=episode.premiered or show.premiered,
        certification=show.certification or episode.certification,
        runtime=episode.runtime,
        genres=show.genres or episode.genres,
        styles=show.styles or episode.styles,
        composers=show.composers or episode.composers,
        status=show.status,
        countries=show.countries or episode.countries,
        tagline=show.tagline,
        plot=episode.plot or show.plot,
        lyrics=episode.lyrics,
        synced_lyrics=episode.synced_lyrics,
        tags=episode.tags or show.tags,
        ids={**(show.ids or {}), **(episode.ids or {})},
        rating=episode.rating if episode.rating is not None else show.rating,
        rating_source=episode.rating_source or show.rating_source,
        studios=show.studios or episode.studios,
        cast=episode.cast or show.cast,
    )


def _first_metadata(
    paths: list[Path],
    context: OrganizerScanContext | None = None,
) -> LocalMetadata:
    for path in paths:
        metadata = _read_metadata_file(path, context)
        if metadata.exists:
            return metadata
    return LocalMetadata()


def _read_metadata_file(
    metadata_path: Path,
    context: OrganizerScanContext | None = None,
) -> LocalMetadata:
    key = metadata_path.expanduser().resolve()
    if context and key in context.metadata:
        return context.metadata[key]
    if not metadata_path.exists():
        metadata = LocalMetadata()
        if context:
            context.metadata[key] = metadata
        return metadata
    try:
        root = ET.parse(metadata_path).getroot()
    except ET.ParseError:
        metadata = LocalMetadata(exists=True)
        if context:
            context.metadata[key] = metadata
        return metadata
    rating, rating_source = _metadata_rating(root)
    metadata = LocalMetadata(
        exists=True,
        title=_metadata_text(root, "title"),
        original_title=_metadata_text(root, "originaltitle"),
        show_title=_metadata_text(root, "showtitle"),
        artist=_metadata_text(root, "artist"),
        album=_metadata_text(root, "album"),
        year=_metadata_year(root),
        premiered=_metadata_text(root, "premiered") or _metadata_text(root, "aired"),
        certification=_metadata_text(root, "certification") or _metadata_text(root, "mpaa"),
        runtime=_int_from_text(_metadata_text(root, "runtime")),
        genres=_metadata_split_texts(root, "genre", limit=8),
        styles=_metadata_split_texts(root, "style", limit=8),
        composers=_metadata_split_texts(root, "composer", limit=8),
        status=_metadata_text(root, "status"),
        countries=_metadata_split_texts(root, "country", limit=4),
        tagline=_metadata_text(root, "tagline"),
        plot=_metadata_text(root, "plot") or _metadata_text(root, "review"),
        lyrics=_metadata_text(root, "lyrics"),
        synced_lyrics=_metadata_text(root, "syncedlyrics"),
        tags=_metadata_split_texts(root, "tag", limit=16),
        ids=_metadata_ids(root),
        rating=rating,
        rating_source=rating_source,
        studios=_metadata_texts(root, "studio", limit=3),
        cast=_metadata_actor_names(root, limit=4),
    )
    if context:
        context.metadata[key] = metadata
    return metadata


def _metadata_paths(
    path: Path,
    media_type: str,
    context: OrganizerScanContext | None = None,
) -> list[Path]:
    if media_type == "tv":
        candidates = [
            path.parent.parent / "tvshow.nfo",
            path.parent / "tvshow.nfo",
            path.with_suffix(".nfo"),
        ]
    else:
        candidates = [
            path.with_suffix(".nfo"),
            path.parent / "movie.nfo",
            path.parent / "album.nfo",
        ]
    adjacent_nfos = [] if media_type == "track" else _adjacent_nfo_files(path.parent, context)
    if media_type != "tv" or len(adjacent_nfos) == 1:
        candidates.extend(adjacent_nfos)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.expanduser().resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(candidate)
    return deduped


def _adjacent_nfo_files(path: Path, context: OrganizerScanContext | None = None) -> list[Path]:
    children = context.list_children(path) if context else (
        sorted(path.iterdir(), key=lambda item: item.name.lower()) if path.is_dir() else []
    )
    return sorted(
        (
            child
            for child in children
            if child.is_file()
            and child.suffix.lower() == ".nfo"
            and not child.name.startswith("._")
        ),
        key=lambda child: child.name.lower(),
    )


def _metadata_text(root: ET.Element, tag: str) -> str | None:
    value = root.findtext(f".//{tag}")
    if not value or not value.strip():
        return None
    return value.strip()


def _metadata_texts(root: ET.Element, tag: str, *, limit: int) -> list[str]:
    values: list[str] = []
    for element in root.findall(f".//{tag}"):
        if element.text and element.text.strip():
            values.append(element.text.strip())
        if len(values) >= limit:
            break
    return values


def _metadata_split_texts(root: ET.Element, tag: str, *, limit: int) -> list[str]:
    values: list[str] = []
    for value in _metadata_texts(root, tag, limit=limit):
        for part in value.replace("/", ",").split(","):
            text = part.strip()
            if text:
                values.append(text)
            if len(values) >= limit:
                return values
    return values


def _metadata_actor_names(root: ET.Element, *, limit: int) -> list[str]:
    values: list[str] = []
    for actor in root.findall(".//actor"):
        name = actor.findtext("name")
        if name and name.strip():
            values.append(name.strip())
        if len(values) >= limit:
            break
    return values


def _metadata_year(root: ET.Element) -> int | None:
    for tag in ("year", "premiered", "aired", "released"):
        year = _year_from_text(root.findtext(f".//{tag}"))
        if year is not None:
            return year
    return None


def _metadata_rating(root: ET.Element) -> tuple[float | None, str | None]:
    for element in root.findall(".//ratings/rating"):
        rating = _float_from_text(element.findtext("value") or element.text)
        if rating is not None:
            return rating, _rating_source(element) or "NFO"

    for element in root.findall(".//rating"):
        rating = _float_from_text(element.findtext("value") or element.text)
        if rating is not None:
            return rating, _rating_source(element) or "NFO"

    user_rating = _float_from_text(root.findtext(".//userrating"))
    if user_rating is not None:
        return user_rating, "User"
    return None, None


def _rating_source(element: ET.Element) -> str:
    return (element.attrib.get("name") or element.attrib.get("type") or "").strip()


def _year_from_text(value: str | None) -> int | None:
    if not value or len(value.strip()) < 4:
        return None
    try:
        year = int(value.strip()[:4])
    except ValueError:
        return None
    return year if 1800 <= year <= 2200 else None


def _float_from_text(value: str | None) -> float | None:
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _int_from_text(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    try:
        return int(float(value.strip()))
    except ValueError:
        return None


def _metadata_ids(root: ET.Element) -> dict[str, str]:
    ids: dict[str, str] = {}
    for element in root.findall(".//uniqueid"):
        source = (element.attrib.get("type") or "id").strip().lower()
        value = (element.text or "").strip()
        if source and value:
            ids[source] = value
    for tag, source in (
        ("imdbid", "imdb"),
        ("tmdbid", "tmdb"),
        ("tvdbid", "tvdb"),
        ("wikidataid", "wikidata"),
        ("id", "id"),
    ):
        value = _metadata_text(root, tag)
        if value:
            ids.setdefault(source, value)
    return ids
