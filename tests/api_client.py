from __future__ import annotations

import asyncio
from typing import Any

import httpx


class ASGITestClient:
    def __init__(self, app) -> None:
        self._app = app

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", path, **kwargs)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._request(method, path, **kwargs))

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)
