from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from mm.db.client import AsyncDBClient
from mm.io import local_storage
from mm.server.routers import (
    albums,
    auth,
    batch,
    files,
    importer,
    jobs,
    library,
    media,
    music,
    organizer,
    player,
    stats,
    tags,
    users,
    videos,
)
from mm.server.routers import smart_albums as smart_albums_router
from mm.server.routers.jobs import resume_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = AsyncDBClient(app.state.db_path)
    await db.connect()
    await db.init_db()
    app.state.db = db
    app.state.config = await db.library_config.get()
    app.state.library_generation = 0
    app.state.library_event_subscribers = set()
    app.state.media_ticket_secret = secrets.token_bytes(32)
    await resume_jobs(db)
    try:
        yield
    finally:
        current_db: AsyncDBClient = getattr(app.state, "db", db)
        await current_db.close()
        if current_db is not db:
            await db.close()


def create_app(db_path: str | Path) -> FastAPI:
    app = FastAPI(title="Media Library", version="3.0.0", lifespan=lifespan)
    app.state.db_path = db_path

    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    for r in (
        auth,
        users,
        media,
        music,
        tags,
        stats,
        batch,
        files,
        albums,
        smart_albums_router,
        library,
        organizer,
        player,
        videos,
        importer,
        jobs,
    ):
        app.include_router(r.router)

    # Prefer an explicitly configured or freshly built source checkout. Wheels
    # fall back to the bundled dist copied in by the build backend.
    web_dist = resolve_web_dist()

    if local_storage.is_dir(web_dist):
        assets_dir = web_dist / "assets"
        if local_storage.is_dir(assets_dir):
            app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="frontend-assets",
            )

        @app.get("/vite.svg")
        async def vite_svg():
            svg = web_dist / "vite.svg"
            return (
                FileResponse(str(svg), media_type="image/svg+xml")
                if local_storage.exists(svg)
                else HTMLResponse(status_code=404)
            )

        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str):
            if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
                return HTMLResponse(status_code=404)
            index = web_dist / "index.html"
            return (
                FileResponse(
                    str(index),
                    media_type="text/html",
                    headers={"Cache-Control": "no-cache"},
                )
                if local_storage.exists(index)
                else HTMLResponse(status_code=404)
            )

    return app


def resolve_web_dist(
    *,
    module_file: str | Path = __file__,
    env: Mapping[str, str] = os.environ,
) -> Path:
    configured = env.get("MM_WEB_DIST")
    module_path = Path(module_file).resolve()
    embedded = module_path.parent.parent / "_web_dist"
    candidates = [
        Path(configured).expanduser() if configured else None,
        module_path.parents[3] / "web" / "dist",
        embedded,
    ]
    return next(
        (candidate for candidate in candidates if candidate and local_storage.is_dir(candidate)),
        embedded,
    )


# ASGI entry point
db_path_env = os.environ.get("MM_DB", "mm.db")
app = create_app(db_path_env)
