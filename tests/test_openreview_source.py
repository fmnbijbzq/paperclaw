from pathlib import Path
import sys

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.sources.openreview import OpenReviewSource


def test_openreview_source_parses_note_payload(monkeypatch):
    captured_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "notes": [
                    {
                        "id": "note-1",
                        "content": {
                            "title": {"value": "OpenReview Vision Paper"},
                            "abstract": {"value": "Abstract"},
                            "authors": {"value": ["Alice", "Bob"]},
                            "venue": {"value": "CVPR 2026"},
                        },
                        "cdate": 1774224000000,
                        "mdate": 1774224000000,
                        "details": {"pdf": "/pdf/note-1.pdf"},
                        "forum": "forum-1",
                    }
                ]
            },
        )

    source = OpenReviewSource(
        base_url="https://example.test",
        venues=["CVPR"],
        transport=httpx.MockTransport(handler),
    )
    monkeypatch.setattr(source, "_fetch_full_text", lambda pdf_url: None)

    records = source.fetch()

    assert captured_paths == ["/notes"]
    assert len(records) == 1
    assert records[0].source == "openreview"
    assert records[0].source_paper_id == "note-1"
    assert records[0].title == "OpenReview Vision Paper"
    assert records[0].abstract == "Abstract"
    assert records[0].authors == ["Alice", "Bob"]
    assert records[0].venue == "CVPR 2026"
    assert records[0].paper_url == "https://example.test/forum?id=forum-1"
    assert records[0].pdf_url == "https://example.test/pdf/note-1.pdf"


def test_openreview_source_builds_default_openreview_urls_without_details_pdf():
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "notes": [
                    {
                        "id": "note-default",
                        "content": {
                            "title": {"value": "Default API Paper"},
                            "venue": {"value": "CVPR 2026"},
                        },
                        "forum": "forum-default",
                    }
                ]
            },
        )

    source = OpenReviewSource(
        venues=["CVPR"],
        transport=httpx.MockTransport(handler),
    )

    records = source.fetch()

    assert captured_urls[0].startswith("https://api2.openreview.net/notes?")
    assert len(records) == 1
    assert records[0].paper_url == "https://openreview.net/forum?id=forum-default"
    assert records[0].pdf_url == "https://openreview.net/pdf?id=note-default"


def test_openreview_source_filters_venues():
    source = OpenReviewSource(
        base_url="https://example.test",
        venues=["CVPR"],
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "notes": [
                        {
                            "id": "note-1",
                            "content": {"title": {"value": "Paper A"}},
                            "forum": "forum-1",
                            "venue": "CVPR 2026",
                        },
                        {
                            "id": "note-2",
                            "content": {"title": {"value": "Paper B"}},
                            "forum": "forum-2",
                            "venue": "NeurIPS 2026",
                        },
                    ]
                },
            )
        ),
    )

    records = source.fetch()

    assert [record.source_paper_id for record in records] == ["note-1"]


def test_openreview_source_includes_lookback_window_in_query():
    captured_requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(str(request.url))
        return httpx.Response(200, json={"notes": []})

    source = OpenReviewSource(
        base_url="https://example.test",
        venues=["CVPR"],
        lookback_days=7,
        transport=httpx.MockTransport(handler),
    )

    source.fetch()

    assert len(captured_requests) == 1
    assert "mintcdate=" in captured_requests[0]
    assert "content.venue=CVPR" in captured_requests[0]


def test_openreview_source_queries_each_configured_venue_once():
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json={"notes": []})

    source = OpenReviewSource(
        base_url="https://example.test",
        venues=["CVPR", "ICCV"],
        transport=httpx.MockTransport(handler),
    )

    source.fetch()

    assert len(captured_urls) == 2
    assert "content.venue=CVPR" in captured_urls[0]
    assert "content.venue=ICCV" in captured_urls[1]


def test_openreview_source_fetches_full_text_from_pdf(monkeypatch):
    source = OpenReviewSource(
        base_url="https://example.test",
        venues=["CVPR"],
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "notes": [
                        {
                            "id": "note-1",
                            "content": {
                                "title": {"value": "OpenReview Vision Paper"},
                                "abstract": {"value": "Abstract"},
                                "authors": {"value": ["Alice", "Bob"]},
                            },
                            "details": {"pdf": "/pdf/note-1.pdf"},
                            "forum": "forum-1",
                            "venue": "CVPR 2026",
                        }
                    ]
                },
            )
        ),
    )

    monkeypatch.setattr(source, "_fetch_full_text", lambda pdf_url: "OpenReview full text")

    records = source.fetch()

    assert len(records) == 1
    assert records[0].full_text == "OpenReview full text"
