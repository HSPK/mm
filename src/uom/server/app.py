"""FastAPI application — REST API for UOM media library.

Features:
- User authentication (token-based, setup wizard for first user)
- Pydantic models for all request / response schemas
- Proper video streaming with HTTP range requests
- Rating, timeline, cameras, random, batch operations
- Tag management (CRUD, rename, delete, batch add/remove)
- Separated concerns: route registration is modular
"""

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
from uom.server.routers import albums, auth, batch, media, stats, tags, users

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    repo = AsyncRepository(app.state.db_path)
    await repo.connect()
    await repo.init_db()
    app.state.repo = repo
    yield
    # --- Shutdown ---
    # repo.close() if implemented


def create_app(db_path: str | Path) -> FastAPI:
    """Build and return the FastAPI app with all routes registered."""
    app = FastAPI(title="UOM Media Library", version="3.0.0", lifespan=lifespan)
    app.state.db_path = db_path

    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Allow CORS for frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Shared state ---
    # repo = Repository(db_path)
    # repo.connect()
    # repo.init_db()
    # app.state.repo = repo
    app.state.db_path = db_path

    # --- Register routes ---
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(media.router)
    app.include_router(tags.router)
    app.include_router(stats.router)
    app.include_router(batch.router)
    app.include_router(albums.router)

    # --- Serve frontend static files (built dist) ---
    web_dist = Path(os.environ.get("UOM_WEB_DIST", "web/dist"))
    if not web_dist.is_dir():
        # Try common relative locations
        for candidate in [
            Path(__file__).resolve().parents[3] / "web" / "dist",
            Path.cwd() / "web" / "dist",
        ]:
            if candidate.is_dir():
                web_dist = candidate
                break

    if web_dist.is_dir():
        # Serve /assets (js, css, etc.) from dist/assets
        assets_dir = web_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

        # Serve other static files at root (favicon, etc.)
        @app.get("/vite.svg")
        async def vite_svg():
            svg = web_dist / "vite.svg"
            if svg.exists():
                return FileResponse(str(svg), media_type="image/svg+xml")

        # SPA fallback: serve index.html for all non-API routes
        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str):
            # Don't intercept API or known backend paths
            if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
                return HTMLResponse(status_code=404)
            index = web_dist / "index.html"
            if index.exists():
                return FileResponse(str(index), media_type="text/html")
            return HTMLResponse(status_code=404)

    return app


# ---------------------------------------------------------------------------
# ASGI factory (used by uvicorn)
# ---------------------------------------------------------------------------


# Initialize the global app instance for uvicorn standard usage

db_path_env = os.environ.get("UOM_DB", "uom.db")
app = create_app(db_path_env)


def _asgi_app() -> FastAPI:
    """Factory called by uvicorn to create the ASGI app."""
    return create_app(db_path_env)
