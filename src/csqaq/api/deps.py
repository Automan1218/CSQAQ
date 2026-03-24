# src/csqaq/api/deps.py
"""FastAPI dependency injection."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

if TYPE_CHECKING:
    from csqaq.main import App

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app(request: Request) -> App:
    """Get the App container from FastAPI app state."""
    return request.app.state.app


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    app: App = Depends(get_app),
) -> dict:
    """Require a valid JWT token. Returns user payload dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from csqaq.api.routes.auth import verify_access_token

    payload = verify_access_token(credentials.credentials, app.settings.secret_key)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    app: App = Depends(get_app),
) -> dict | None:
    """Optionally extract user from JWT. Returns None if no token or invalid."""
    if credentials is None:
        return None
    from csqaq.api.routes.auth import verify_access_token

    return verify_access_token(credentials.credentials, app.settings.secret_key)
