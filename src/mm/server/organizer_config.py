from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from mm.config import CliConfig, load_cli_config, save_cli_config
from mm.server.organizer_schemas import (
    OrganizerConfigPatch,
    OrganizerConfigResponse,
    OrganizerSourceStatus,
)

IMPLEMENTED_SCRAPERS = {"tmdb", "omdb", "musicbrainz", "itunes", "netease", "qqmusic"}


def organizer_config_response(cfg: CliConfig | None = None) -> OrganizerConfigResponse:
    cfg = cfg or load_cli_config()
    return OrganizerConfigResponse(
        language=cfg.scrapers.language,
        chinese_script=cfg.organizer.chinese_script,
        lyrics_source=cfg.organizer.lyrics_source,
        timeout=cfg.scrapers.timeout,
        order=cfg.scrapers.order,
        sources=[
            OrganizerSourceStatus(
                name=name,
                enabled=source.enabled,
                implemented=name in IMPLEMENTED_SCRAPERS,
                has_credentials=any(value.strip() for value in source.credentials.values()),
                base_url=source.base_url,
                priority=source.priority,
            )
            for name, source in sorted(
                cfg.scrapers.sources.items(),
                key=lambda item: item[1].priority,
            )
        ],
        templates=cfg.organizer.templates.model_dump(mode="json"),
        default_scrapers=cfg.organizer.default_scrapers,
        media_sources=cfg.organizer.media_sources,
    )


def update_organizer_config_patch(body: OrganizerConfigPatch) -> OrganizerConfigResponse:
    cfg = load_cli_config()
    if body.language is not None:
        cfg.scrapers.language = body.language
    if body.timeout is not None:
        cfg.scrapers.timeout = body.timeout
    if body.order is not None:
        cfg.scrapers.order = body.order
    if body.source:
        _update_source(cfg, body)
    if body.templates:
        _update_templates(cfg, body.templates)
    if body.chinese_script is not None:
        if body.chinese_script not in {"simplified", "traditional"}:
            raise HTTPException(400, "Unknown Chinese script")
        cfg.organizer.chinese_script = body.chinese_script
    if body.lyrics_source is not None:
        if body.lyrics_source not in {"lrclib", "netease", "qq", "all"}:
            raise HTTPException(400, "Unknown lyrics source")
        cfg.organizer.lyrics_source = body.lyrics_source
    if body.default_scrapers is not None:
        cfg.organizer.default_scrapers = {
            key: value
            for key, value in body.default_scrapers.items()
            if key in {"movies", "tv", "music"} and value in cfg.scrapers.sources
        }
    if body.media_sources is not None:
        cfg.organizer.media_sources = {
            key: [str(Path(value).expanduser()) for value in values]
            for key, values in body.media_sources.items()
            if key in {"movies", "tv", "music"}
        }
    save_cli_config(cfg)
    return organizer_config_response(load_cli_config())


def _update_source(cfg: CliConfig, body: OrganizerConfigPatch) -> None:
    source = cfg.scrapers.sources.get(body.source or "")
    if not source:
        raise HTTPException(404, f"Unknown source: {body.source}")
    if body.enabled is not None:
        source.enabled = body.enabled
    if body.base_url is not None:
        source.base_url = body.base_url
    if body.priority is not None:
        source.priority = body.priority
    if body.credentials is not None:
        source.credentials = {
            **source.credentials,
            **{key: value for key, value in body.credentials.items() if value.strip()},
        }


def _update_templates(cfg: CliConfig, templates: dict[str, str]) -> None:
    for key, value in templates.items():
        if not hasattr(cfg.organizer.templates, key):
            raise HTTPException(400, f"Unknown template: {key}")
        setattr(cfg.organizer.templates, key, value)
