from datetime import datetime, timezone
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.schemas import PaperRecord
from app.storage import Database


class StubNotifier:
    def __init__(self, *, fail_titles: set[str] | None = None):
        self.fail_titles = fail_titles or set()
        self.sent_titles: list[str] = []

    def send_paper(self, paper):
        self.sent_titles.append(paper.title)
        if paper.title in self.fail_titles:
            raise RuntimeError("retry failed")
        return {"ok": True}


def _build_paper(source_paper_id: str, title: str, source: str) -> PaperRecord:
    now = datetime(2026, 4, 26, 6, 0, tzinfo=timezone.utc)
    return PaperRecord(
        source=source,
        source_paper_id=source_paper_id,
        dedup_key=f"{source_paper_id}|{title.lower()}",
        title=title,
        abstract="A concise abstract.",
        full_text="Full paper text.",
        authors=["Alice", "Bob"],
        paper_url=f"https://example.com/{source_paper_id}",
        pdf_url=f"https://example.com/{source_paper_id}.pdf",
        venue="Venue",
        categories=["vision"],
        published_at=now,
        updated_at_source=now,
        raw_payload={"id": source_paper_id},
    )


def _seed_notifications(tmp_path: Path) -> None:
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper1 = db.upsert_paper(_build_paper("p1", "First Paper", "arxiv"))
    paper2 = db.upsert_paper(_build_paper("p2", "Second Paper", "openreview"))
    db.record_notification_attempt(destination="feishu", paper=paper1, success=True)
    db.record_notification_attempt(destination="feishu", paper=paper2, success=False, error_message="timeout")


def test_list_notifications_returns_feed_and_counts(tmp_path):
    _seed_notifications(tmp_path)
    client = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path/'papers.db'}",
            editorial_root=tmp_path / "outputs" / "editorial",
        )
    )

    response = client.get("/notifications")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["dataSource"] == "http"
    assert payload["data"]["total"] == 2
    assert payload["data"]["failedCount"] == 1
    assert payload["data"]["successfulCount"] == 1
    items = payload["data"]["items"]
    assert items[0]["notification"]["destination"] == "feishu"
    assert items[0]["paperTitle"] in {"First Paper", "Second Paper"}
    assert items[0]["source"] in {"arxiv", "openreview"}


def test_retry_notifications_supports_batch_and_records_results(tmp_path):
    _seed_notifications(tmp_path)
    app = create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
    )
    app.state.notification_notifier = StubNotifier(fail_titles={"Second Paper"})
    client = TestClient(app)

    response = client.post("/notifications/retry", json={"paperIds": [1, 2]})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["requested"] == 2
    assert payload["attempted"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert {item["title"] for item in payload["items"]} == {"First Paper", "Second Paper"}

    feed = client.get("/notifications").json()["data"]
    assert feed["total"] == 4
    assert feed["failedCount"] == 2
    assert feed["successfulCount"] == 2



def test_retry_notifications_accepts_notification_ids(tmp_path):
    _seed_notifications(tmp_path)
    app = create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
    )
    app.state.notification_notifier = StubNotifier()
    client = TestClient(app)

    response = client.post("/notifications/retry", json={"notificationIds": [2]})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["attempted"] == 1
    assert payload["items"][0]["paperId"] == 2
