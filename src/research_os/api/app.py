"""FastAPI application for research-os."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from research_os.api.routes import router
from research_os.config import Config
from research_os.store.db import get_connection, init_schema
from research_os.store.store import Store

_store: Store | None = None


def get_store() -> Store:
    if _store is None:
        raise RuntimeError("Store not initialized")
    return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store
    cfg = Config()
    conn = get_connection(cfg.db_path, check_same_thread=False)
    init_schema(conn)
    _store = Store(conn)
    yield
    conn.close()


def create_app() -> FastAPI:
    app = FastAPI(title="research-os", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    # Serve frontend static files in production
    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()
