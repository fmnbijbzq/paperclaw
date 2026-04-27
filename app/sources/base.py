from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO
import logging

import httpx
from pypdf import PdfReader

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
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def fetch(self) -> list[PaperRecord]:
        raise NotImplementedError

    def _get(self, *, params: dict[str, str | int]) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return response

    def _get_url(self, url: str) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            response = client.get(url)
            response.raise_for_status()
            return response

    def _fetch_full_text(self, pdf_url: str | None) -> str | None:
        if not pdf_url:
            return None

        try:
            response = self._get_url(pdf_url)
            reader = PdfReader(BytesIO(response.content))
            pages = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n".join(part.strip() for part in pages if part and part.strip()).strip()
            return full_text or None
        except Exception as exc:
            self.logger.warning("Failed to fetch full text from %s: %s", pdf_url, exc)
            return None
