from pathlib import Path
import sys

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.sources.arxiv import ArxivSource


def test_arxiv_source_parses_atom_entry():
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        if request.url.path.endswith(".pdf"):
            return httpx.Response(status_code=404)
        return httpx.Response(
            200,
            text="""<?xml version='1.0'?>
            <feed xmlns='http://www.w3.org/2005/Atom'>
              <entry>
                <id>http://arxiv.org/abs/1234.5678v1</id>
                <title> Vision   Paper </title>
                <summary> Abstract text </summary>
                <published>2026-03-23T00:00:00Z</published>
                <updated>2026-03-23T01:00:00Z</updated>
                <author><name>Alice</name></author>
                <author><name>Bob</name></author>
                <link title='pdf' href='http://arxiv.org/pdf/1234.5678v1'/>
                <category term='cs.CV'/>
              </entry>
            </feed>""",
        )

    source = ArxivSource(
        base_url="https://example.test/api/query",
        transport=httpx.MockTransport(handler),
    )

    records = source.fetch()

    assert len(records) == 1
    assert records[0].source == "arxiv"
    assert records[0].source_paper_id == "1234.5678v1"
    assert records[0].title == "Vision Paper"
    assert records[0].abstract == "Abstract text"
    assert records[0].authors == ["Alice", "Bob"]
    assert records[0].paper_url == "http://arxiv.org/abs/1234.5678v1"
    assert records[0].pdf_url == "http://arxiv.org/pdf/1234.5678v1"
    assert records[0].categories == ["cs.CV"]
    assert any("search_query" in url for url in captured_urls)


def test_arxiv_source_filters_categories():
    source = ArxivSource(
        base_url="https://example.test/api/query",
        allowed_categories=["cs.CV"],
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                text="""<?xml version='1.0'?>
                <feed xmlns='http://www.w3.org/2005/Atom'>
                  <entry>
                    <id>http://arxiv.org/abs/1234.5678v1</id>
                    <title> Vision Paper </title>
                    <summary>Abstract text</summary>
                    <published>2026-03-23T00:00:00Z</published>
                    <updated>2026-03-23T00:00:00Z</updated>
                    <author><name>Alice</name></author>
                    <category term='cs.CV'/>
                  </entry>
                  <entry>
                    <id>http://arxiv.org/abs/9999.0001v1</id>
                    <title> NLP Paper </title>
                    <summary>Other abstract</summary>
                    <published>2026-03-23T00:00:00Z</published>
                    <updated>2026-03-23T00:00:00Z</updated>
                    <author><name>Carol</name></author>
                    <category term='cs.CL'/>
                  </entry>
                </feed>""",
            )
        ),
    )

    records = source.fetch()

    assert [record.source_paper_id for record in records] == ["1234.5678v1"]


def test_arxiv_source_includes_lookback_window_in_query():
    captured_request: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        return httpx.Response(200, text="<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>")

    source = ArxivSource(
        base_url="https://example.test/api/query",
        lookback_days=3,
        transport=httpx.MockTransport(handler),
    )

    source.fetch()

    assert "submittedDate%3A%5B" in captured_request["url"]
    assert "TO+%2A" not in captured_request["url"]
    assert "TO%20%2A" not in captured_request["url"]


def test_arxiv_source_sorts_by_latest_submitted_date_by_default():
    captured_request: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        return httpx.Response(200, text="<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'></feed>")

    source = ArxivSource(
        base_url="https://example.test/api/query",
        transport=httpx.MockTransport(handler),
    )

    source.fetch()

    assert "sortBy=submittedDate" in captured_request["url"]
    assert "sortOrder=descending" in captured_request["url"]


def test_arxiv_source_fetches_full_text_from_pdf(monkeypatch):
    source = ArxivSource(
        base_url="https://example.test/api/query",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                text="""<?xml version='1.0'?>
                <feed xmlns='http://www.w3.org/2005/Atom'>
                  <entry>
                    <id>http://arxiv.org/abs/1234.5678v1</id>
                    <title> Vision Paper </title>
                    <summary>Abstract text</summary>
                    <author><name>Alice</name></author>
                    <link title='pdf' href='http://arxiv.org/pdf/1234.5678v1'/>
                    <category term='cs.CV'/>
                  </entry>
                </feed>""",
            )
        ),
    )

    monkeypatch.setattr(source, "_fetch_full_text", lambda pdf_url: "Full paper body text")

    records = source.fetch()

    assert len(records) == 1
    assert records[0].full_text == "Full paper body text"
