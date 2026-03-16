"""FastAPI application — REST API for UOM media library."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from uom.db.async_repository import AsyncRepository
from uom.server.routers import albums, auth, batch, library, media, stats, tags, users
from uom.server.routers import smart_albums as smart_albums_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = AsyncRepository(app.state.db_path)
    await repo.connect()
    await repo.init_db()
    app.state.repo = repo
    yield


def _derive_library_root(db_path: str | Path) -> str:
    """Derive the library root directory (parent of the DB file)."""
    return str(Path(db_path).resolve().parent)


def create_app(db_path: str | Path) -> FastAPI:
    app = FastAPI(title="UOM Media Library", version="3.0.0", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.library_root = _derive_library_root(db_path)

    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    for r in (auth, users, media, tags, stats, batch, albums, smart_albums_router, library):
        app.include_router(r.router)

    # Serve frontend static files
    web_dist = Path(os.environ.get("UOM_WEB_DIST", "web/dist"))
    if not web_dist.is_dir():
        for candidate in [
            Path(__file__).resolve().parents[3] / "web" / "dist",
            Path.cwd() / "web" / "dist",
        ]:
            if candidate.is_dir():
                web_dist = candidate
                break

    if web_dist.is_dir():
        assets_dir = web_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

        @app.get("/vite.svg")
        async def vite_svg():
            svg = web_dist / "vite.svg"
            return (
                FileResponse(str(svg), media_type="image/svg+xml")
                if svg.exists()
                else HTMLResponse(status_code=404)
            )

        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str):
            if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
                return HTMLResponse(status_code=404)
            index = web_dist / "index.html"
            return (
                FileResponse(str(index), media_type="text/html")
                if index.exists()
                else HTMLResponse(status_code=404)
            )

    return app


# ASGI entry point
db_path_env = os.environ.get("UOM_DB", "uom.db")
app = create_app(db_path_env)
