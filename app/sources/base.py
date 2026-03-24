from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.schemas import PaperRecord


class BaseSource(ABC):
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._transport = transport

    @abstractmethod
    def fetch(self) -> list[PaperRecord]:
        raise NotImplementedError

    def _get(self, *, params: dict[str, str | int]) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return response
