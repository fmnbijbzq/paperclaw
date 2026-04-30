"""Smoke test for destination API endpoints."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.api.app import create_app
from app.schemas import PaperRecord
from app.storage import Database
from tests.api_client import ASGITestClient


def test_list_destinations_empty(tmp_path):
    db_path = tmp_path / "papers.db"
    app = create_app(database_url=f"sqlite:///{db_path}")
    client = ASGITestClient(app)

    resp = client.get("/destinations")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


def test_create_and_list_destinations(tmp_path):
    db_path = tmp_path / "papers.db"
    db = Database(f"sqlite:///{db_path}")
    db.create_schema()

    paper = db.upsert_paper(PaperRecord(
        source="test", source_paper_id="t1", title="Test Paper",
        authors=["Author"], paper_url="http://example.com",
    ))
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id, platform="bilibili",
        title="Test Draft", hook="Hook", markdown_content="Content",
        output_path=str(tmp_path / "test.md"),
    )

    app = create_app(database_url=f"sqlite:///{db_path}")
    client = ASGITestClient(app)

    # POST /destinations
    resp = client.post("/destinations", json={
        "draftId": draft.draft_id,
        "platform": "bilibili",
        "status": "published",
        "publishResult": {"externalUrl": "https://bilibili.com/video/123"},
    })
    assert resp.status_code == 200
    dest = resp.json()["data"]
    assert dest["platform"] == "bilibili"
    assert dest["status"] == "published"
    dest_id = dest["destinationId"]

    # GET /destinations/{draft_id}
    resp = client.get(f"/destinations/{draft.draft_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1

    # GET /destinations with query param
    resp = client.get("/destinations?draft_id=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0

    # PATCH /destinations/{id}
    resp = client.patch(f"/destinations/{dest_id}", json={
        "status": "failed",
        "publishResult": {"error": "timeout"},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"

    # POST with invalid draft_id -> 404
    resp = client.post("/destinations", json={
        "draftId": "nonexistent",
        "platform": "bilibili",
    })
    assert resp.status_code == 404


def test_create_destination_via_manual_publish_result(tmp_path):
    """Record a manual publish result via the POST /destinations endpoint."""
    db_path = tmp_path / "papers.db"
    db = Database(f"sqlite:///{db_path}")
    db.create_schema()

    paper = db.upsert_paper(PaperRecord(
        source="test", source_paper_id="t2", title="Another Paper",
        authors=["Author"], paper_url="http://example.com/2",
    ))
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id, platform="xiaohongshu",
        title="XHS Draft", hook="Hook", markdown_content="Content",
        output_path=str(tmp_path / "xhs.md"),
    )

    app = create_app(database_url=f"sqlite:///{db_path}")
    client = ASGITestClient(app)

    # Record a manual publish
    resp = client.post("/destinations", json={
        "draftId": draft.draft_id,
        "platform": "xiaohongshu",
        "status": "published",
        "publishResult": {
            "method": "manual",
            "note": "Published by editor manually",
            "url": "https://www.xiaohongshu.com/explore/abc123",
        },
    })
    assert resp.status_code == 200
    dest = resp.json()["data"]
    assert dest["platform"] == "xiaohongshu"
    assert dest["status"] == "published"
    assert dest["publishResult"]["method"] == "manual"

    # Verify it appears in the list
    resp = client.get(f"/destinations/{draft.draft_id}")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["platform"] == "xiaohongshu"
