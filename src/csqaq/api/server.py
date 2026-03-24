# src/csqaq/api/server.py
"""FastAPI application factory and uvicorn launcher."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from csqaq.main import App


def create_app(app_container: App | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        app_container: Pre-initialized App instance (for testing).
            If None, creates and initializes one from Settings.
    """

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        nonlocal app_container
        if app_container is None:
            from csqaq.config import Settings
            from csqaq.main import App, setup_logging

            setup_logging()
            settings = Settings(mode="server")
            app_container = App(settings)
            await app_container.init()

        fastapi_app.state.app = app_container
        yield

        if app_container is not None:
            await app_container.close()

    fastapi_app = FastAPI(
        title="CSQAQ API",
        description="CS2 饰品投资分析系统 API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "https://csqaq.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from csqaq.api.routes import register_routes

    register_routes(fastapi_app)

    return fastapi_app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Launch uvicorn server."""
    import uvicorn

    uvicorn.run(
        "csqaq.api.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )
