from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import yaml

from mm.config import CliConfig
from mm.server.organizer_schemas import OrganizerItem
from mm.server.organizer_sources import OrganizerSourceResolver


def benchmark(item_count: int, baseline_sample: int) -> dict[str, float | int]:
    root = Path(tempfile.gettempdir()) / "mm-organizer-source-benchmark"
    cfg = CliConfig()
    cfg.organizer.media_sources = {
        "movies": [str(root / "Movies")],
        "tv": [str(root / "Shows")],
        "music": [str(root / "Music")],
    }
    items = [
        OrganizerItem(
            path=str(
                root
                / "Music"
                / f"Artist {index // 100:04d}"
                / f"Album {index // 10:05d}"
                / f"{index:06d}.flac"
            ),
            media_type="track",
            title=f"Track {index}",
        )
        for index in range(item_count)
    ]
    config_yaml = yaml.safe_dump(cfg.model_dump(mode="json", by_alias=True))

    sample_count = min(item_count, baseline_sample)
    baseline_started = time.perf_counter()
    for item in items[:sample_count]:
        for _ in range(3):
            loaded_cfg = CliConfig.model_validate(yaml.safe_load(config_yaml))
            OrganizerSourceResolver.from_config(loaded_cfg).resolve_item(item)
    baseline_ms = (time.perf_counter() - baseline_started) * 1000

    optimized_started = time.perf_counter()
    loaded_cfg = CliConfig.model_validate(yaml.safe_load(config_yaml))
    resolver = OrganizerSourceResolver.from_config(loaded_cfg)
    resolved = [resolver.resolve_item(item) for item in items]
    optimized_ms = (time.perf_counter() - optimized_started) * 1000

    projected_baseline_ms = baseline_ms / sample_count * item_count
    return {
        "items": item_count,
        "baseline_sample": sample_count,
        "legacy_config_loads": item_count * 3,
        "optimized_config_loads": 1,
        "projected_legacy_ms": round(projected_baseline_ms, 2),
        "optimized_ms": round(optimized_ms, 2),
        "projected_speedup": round(projected_baseline_ms / optimized_ms, 1),
        "resolved_items": sum(
            source.kind == "music" and source.root == (root / "Music").resolve()
            for source in resolved
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=int, default=10_000)
    parser.add_argument("--baseline-sample", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.items, args.baseline_sample), indent=2))


if __name__ == "__main__":
    main()
