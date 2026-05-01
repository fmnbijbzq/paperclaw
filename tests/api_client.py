from __future__ import annotations

import asyncio
from typing import Any

import httpx


TEST_API_KEY = "test-api-key"


class ASGITestClient:
    """Lightweight async-aware ASGI client for tests.

    If ``api_key`` is set (default: ``TEST_API_KEY``), every request is
    auto-decorated with ``Authorization: Bearer <api_key>``. Pass
    ``api_key=None`` to test the unauthenticated path.
    """

    def __init__(self, app, *, api_key: str | None = TEST_API_KEY) -> None:
        self._app = app
        self._api_key = api_key

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if self._api_key is not None:
            headers = dict(kwargs.pop("headers", {}) or {})
            headers.setdefault("Authorization", f"Bearer {self._api_key}")
            kwargs["headers"] = headers
        return asyncio.run(self._request(method, path, **kwargs))

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)
