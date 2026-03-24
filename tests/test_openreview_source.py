from pathlib import Path
import sys

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.sources.openreview import OpenReviewSource


def test_openreview_source_parses_note_payload():
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
                            "cdate": 1774224000000,
                            "mdate": 1774224000000,
                            "details": {"pdf": "/pdf/note-1.pdf"},
                            "forum": "forum-1",
                            "venue": "CVPR 2026",
                        }
                    ]
                },
            )
        ),
    )

    records = source.fetch()

    assert len(records) == 1
    assert records[0].source == "openreview"
    assert records[0].source_paper_id == "note-1"
    assert records[0].title == "OpenReview Vision Paper"
    assert records[0].abstract == "Abstract"
    assert records[0].authors == ["Alice", "Bob"]
    assert records[0].venue == "CVPR 2026"
    assert records[0].paper_url == "https://example.test/forum?id=forum-1"
    assert records[0].pdf_url == "https://example.test/pdf/note-1.pdf"


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
    captured_request: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        return httpx.Response(200, json={"notes": []})

    source = OpenReviewSource(
        base_url="https://example.test",
        lookback_days=7,
        transport=httpx.MockTransport(handler),
    )

    source.fetch()

    assert "mintcdate=" in captured_request["url"]
