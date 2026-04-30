from pathlib import Path
import sys
from types import SimpleNamespace

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.enrichment import extractor as extractor_module
from app.enrichment.chunker import chunk_text
from app.enrichment.extractor import TextExtractor
from app.schemas import PaperRecord


def _build_paper(
    *,
    abstract: str | None = None,
    full_text: str | None = None,
    paper_url: str = "https://example.test/paper",
    pdf_url: str | None = None,
) -> PaperRecord:
    return PaperRecord(
        source="demo",
        source_paper_id="demo-1",
        title="Demo Paper",
        abstract=abstract,
        full_text=full_text,
        paper_url=paper_url,
        pdf_url=pdf_url,
    )


def test_extract_paper_text_prefers_stored_full_text_then_abstract():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected network call: {request.url}")

    extractor = TextExtractor(transport=httpx.MockTransport(handler))

    full_text = extractor.extract_paper_text(
        _build_paper(full_text="  Full paper body.  ", abstract="Abstract fallback.")
    )
    abstract = extractor.extract_paper_text(_build_paper(abstract="  Abstract fallback.  "))

    assert full_text.text == "Full paper body."
    assert full_text.source == "full_text"
    assert abstract.text == "Abstract fallback."
    assert abstract.source == "abstract"


def test_extract_paper_text_falls_back_to_landing_page_excerpt(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/paper"
        return httpx.Response(
            200,
            html="""
            <html>
              <body>
                <nav>Navigation should be ignored</nav>
                <article><p>Main article text from the landing page.</p></article>
              </body>
            </html>
            """,
        )

    def fake_extract(html: str, **kwargs) -> str:
        assert kwargs["include_comments"] is False
        assert "Main article text" in html
        return "Main article text from the landing page."

    monkeypatch.setattr(extractor_module, "trafilatura", SimpleNamespace(extract=fake_extract))
    extractor = TextExtractor(transport=httpx.MockTransport(handler))

    result = extractor.extract_paper_text(_build_paper())

    assert result.text == "Main article text from the landing page."
    assert result.source == "landing_page"
    assert result.url == "https://example.test/paper"


def test_extract_pdf_text_fetches_pdf_with_httpx(monkeypatch):
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, stream) -> None:
            assert stream.read() == b"%PDF fake content"
            self.pages = [FakePage(" First page text. "), FakePage("Second page text.")]

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/paper.pdf"
        return httpx.Response(200, content=b"%PDF fake content")

    monkeypatch.setattr(extractor_module, "PdfReader", FakePdfReader)
    extractor = TextExtractor(transport=httpx.MockTransport(handler))

    assert extractor.extract_pdf_text("https://example.test/paper.pdf") == "First page text.\nSecond page text."


def test_chunk_text_preserves_chinese_and_english_paragraph_boundaries():
    text = "第一段介绍方法。\n\nSecond paragraph explains vision models.\n\n第三段给出实验结论。"

    chunks = chunk_text(text, max_tokens=10)

    assert chunks == [
        "第一段介绍方法。",
        "Second paragraph explains vision models.",
        "第三段给出实验结论。",
    ]
