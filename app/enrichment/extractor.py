from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
import logging
import re
from typing import Literal

import httpx

from app.schemas import PaperRecord

try:  # pragma: no cover - exercised through monkeypatch when the dependency is absent.
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None

try:  # pragma: no cover - depends on optional runtime dependency.
    from readability import Document as ReadabilityDocument
except ImportError:  # pragma: no cover
    try:
        from readability.readability import Document as ReadabilityDocument
    except ImportError:
        ReadabilityDocument = None

try:  # pragma: no cover - availability depends on the active environment.
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

ExtractionSource = Literal["full_text", "abstract", "landing_page", "pdf"]


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    source: ExtractionSource
    url: str | None = None


class TextExtractor:
    """Extract paper text from stored fields, PDFs, or landing pages."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.timeout = timeout
        self._transport = transport
        self.logger = logging.getLogger(__name__)

    def extract_paper_text(self, paper: PaperRecord) -> ExtractionResult | None:
        full_text = _normalize_text(paper.full_text)
        if full_text:
            return ExtractionResult(text=full_text, source="full_text")

        abstract = _normalize_text(paper.abstract)
        if abstract:
            return ExtractionResult(text=abstract, source="abstract")

        if paper.paper_url:
            landing_page = self.extract_landing_page_text(paper.paper_url)
            if landing_page:
                return ExtractionResult(text=landing_page, source="landing_page", url=paper.paper_url)

        if paper.pdf_url:
            pdf_text = self.extract_pdf_text(paper.pdf_url)
            if pdf_text:
                return ExtractionResult(text=pdf_text, source="pdf", url=paper.pdf_url)

        return None

    def extract_url_text(self, url: str) -> str | None:
        response = self._get_url(url)
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf"):
            return self._extract_pdf_bytes(response.content)
        return self._extract_html_text(response.text, url=url)

    def extract_pdf_text(self, url: str) -> str | None:
        response = self._get_url(url)
        return self._extract_pdf_bytes(response.content)

    def extract_landing_page_text(self, url: str) -> str | None:
        response = self._get_url(url)
        return self._extract_html_text(response.text, url=url)

    def _get_url(self, url: str) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, transport=self._transport, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response

    def _extract_pdf_bytes(self, content: bytes) -> str | None:
        if PdfReader is None:
            self.logger.warning("pypdf is not available; cannot extract PDF text")
            return None

        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            self.logger.warning("Failed to extract PDF text: %s", exc)
            return None

        return _normalize_text("\n".join(pages))

    def _extract_html_text(self, html: str, *, url: str | None = None) -> str | None:
        trafilatura_text = self._extract_with_trafilatura(html, url=url)
        if trafilatura_text:
            return trafilatura_text

        readability_text = self._extract_with_readability(html)
        if readability_text:
            return readability_text

        parser = _HTMLTextExtractor()
        parser.feed(html)
        return _normalize_text(parser.text)

    @staticmethod
    def _extract_with_trafilatura(html: str, *, url: str | None = None) -> str | None:
        if trafilatura is None:
            return None
        try:
            text = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=False,
            )
        except Exception:
            return None
        return _normalize_text(text)

    @staticmethod
    def _extract_with_readability(html: str) -> str | None:
        if ReadabilityDocument is None:
            return None
        try:
            summary_html = ReadabilityDocument(html).summary()
        except Exception:
            return None
        parser = _HTMLTextExtractor()
        parser.feed(summary_html)
        return _normalize_text(parser.text)


class _HTMLTextExtractor(HTMLParser):
    _IGNORED_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside"}
    _BLOCK_TAGS = {"article", "div", "main", "p", "section", "br", "li", "h1", "h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._ignored_depth = 0

    @property
    def text(self) -> str:
        return " ".join(self._parts)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text)


_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def _strip_unpaired_surrogates(value: str) -> str:
    """Remove UTF-16 surrogate code points from a Python str.

    Python str can hold any code point including bare surrogates; UTF-8
    encoding rejects them. PDF extractors (notably pypdf on mathematical
    italic SMP code points like 𝑥 = U+1D465) sometimes emit unpaired
    high surrogates (e.g. \\ud835). Strip them at the boundary so they
    cannot reach SQLite or downstream JSON.
    """
    return _SURROGATE_RE.sub("", value)


def _normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _strip_unpaired_surrogates(value)
    lines = [" ".join(line.split()) for line in cleaned.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized = "\n".join(line for line in lines if line).strip()
    return normalized or None
