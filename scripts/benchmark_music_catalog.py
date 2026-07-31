from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from mm.db.models import OrganizerMediaModel
from mm.server.music_catalog import _build_music_catalog


def benchmark(track_count: int, tracks_per_album: int) -> dict[str, float | int]:
    root = Path(tempfile.gettempdir()) / "mm-music-benchmark"
    rows = [
        OrganizerMediaModel(
            id=index + 1,
            path=str(
                root
                / f"Artist {index // (tracks_per_album * 10):05d}"
                / f"Album {index // tracks_per_album:06d}"
                / f"{index % tracks_per_album + 1:02d} Track {index:07d}.flac"
            ),
            source_kind="music",
            media_type="track",
            title=f"Track {index:07d}",
            artist=f"Artist {index // (tracks_per_album * 10):05d}",
            album=f"Album {index // tracks_per_album:06d}",
            track=index % tracks_per_album + 1,
            audio_duration=180.0,
            audio_mime_type="audio/flac",
        )
        for index in range(track_count)
    ]
    started = time.perf_counter()
    catalog = _build_music_catalog(rows)
    build_ms = (time.perf_counter() - started) * 1000

    sample_album = next(iter(catalog.tracks_by_album))
    sample_artist = next(iter(catalog.tracks_by_artist))
    lookup_started = time.perf_counter()
    for _ in range(10_000):
        catalog.tracks_by_album[sample_album]
        catalog.tracks_by_artist[sample_artist]
    lookup_ms = (time.perf_counter() - lookup_started) * 1000

    return {
        "tracks": track_count,
        "albums": len(catalog.albums),
        "artists": len(catalog.artists),
        "build_ms": round(build_ms, 2),
        "lookup_10000_ms": round(lookup_ms, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracks", type=int, default=100_000)
    parser.add_argument("--tracks-per-album", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.tracks, args.tracks_per_album), indent=2))


if __name__ == "__main__":
    main()
