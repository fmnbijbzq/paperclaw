"""API key authentication for write operations.

The ``require_api_key`` dependency is **fail-closed**: if no API key is
configured on the server, requests are rejected with HTTP 503 instead of being
silently allowed. This is the opposite of the previous half-finished
``_require_api_key`` shim which fell open when the env var was missing.

Read endpoints (GET) remain public so the dashboard can browse data without
credentials. Mutating endpoints (POST/PATCH/DELETE) must depend on this
function.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_api_key(request: Request) -> str | None:
    """Read the configured API key from app state.

    ``app.state.api_key`` is set by ``create_app`` from ``AppSettings.api_key``
    (env ``API_KEY``). Tests can also inject a value directly.
    """
    return getattr(request.app.state, "api_key", None)


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Validate Bearer token and return an actor identifier for audit fields."""
    expected = _resolve_api_key(request)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key is not configured on the server",
        )
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return f"api:{credentials.credentials[:8]}"
