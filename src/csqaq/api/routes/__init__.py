# src/csqaq/api/routes/__init__.py
"""Route registration."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from csqaq.api.middleware import register_error_handlers

    register_error_handlers(app)

    root = APIRouter(prefix="/api/v1")

    @root.get("/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    app.include_router(root)
