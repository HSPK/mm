"""Declarative organizer extension points exposed to control-plane clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MediaCapability:
    media_type: str
    scrapers: tuple[str, ...]
    outputs: tuple[str, ...]
    rename: bool
    lyrics: bool


MEDIA_CAPABILITIES: tuple[MediaCapability, ...] = (
    MediaCapability("movie", ("tmdb",), ("nfo", "artwork"), True, False),
    MediaCapability("tv", ("tmdb",), ("nfo", "artwork"), True, False),
    MediaCapability(
        "track",
        ("musicbrainz", "itunes", "netease", "qqmusic"),
        ("nfo", "artwork", "lyrics"),
        True,
        True,
    ),
    MediaCapability("album", ("musicbrainz", "itunes"), ("nfo", "artwork"), True, False),
)

# The adapters are centrally declared so routes do not encode source lists.
SCRAPER_ADAPTERS = {
    "tmdb": "tmdb",
    "musicbrainz": "musicbrainz",
    "itunes": "itunes",
    "netease": "netease",
    "qqmusic": "qqmusic",
    "lrclib": "lrclib",
}


def capabilities_response() -> dict[str, object]:
    return {
        "media_types": [asdict(capability) for capability in MEDIA_CAPABILITIES],
        "scraper_adapters": SCRAPER_ADAPTERS,
    }
