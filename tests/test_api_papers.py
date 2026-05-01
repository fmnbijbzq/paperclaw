from datetime import datetime, timezone
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.api.app import create_app
from app.schemas import PaperRecord
from app.storage import Database
from app.summarization.schemas import PaperInsightRecord
from tests.api_client import ASGITestClient


def _build_paper(source_paper_id: str = "2404.01812", title: str = "Sparse Field Priors") -> PaperRecord:
    now = datetime(2026, 4, 26, 6, 0, tzinfo=timezone.utc)
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        dedup_key=f"{source_paper_id}|{title.lower()}",
        title=title,
        abstract="A concise abstract.",
        full_text="Full paper text.",
        authors=["Alice", "Bob"],
        paper_url=f"https://arxiv.org/abs/{source_paper_id}",
        pdf_url=f"https://arxiv.org/pdf/{source_paper_id}.pdf",
        venue="arXiv",
        categories=["3d-vision", "multimodal"],
        published_at=now,
        updated_at_source=now,
        raw_payload={"id": source_paper_id},
    )


def _make_client(tmp_path: Path) -> ASGITestClient:
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    editorial_dir = tmp_path / "outputs" / "editorial"
    app = create_app(database_url=database_url, editorial_root=editorial_dir)
    return ASGITestClient(app)


def _seed_paper_with_insight(tmp_path: Path) -> Database:
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    paper = db.upsert_paper(_build_paper())
    db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="Short summary.",
            summary_long="Long summary.",
            novelty_points=["novel point"],
            limitations=["limitation"],
            applications=["application"],
            confidence_score=0.91,
        ),
    )
    db.record_notification_attempt(destination="feishu", paper=paper, success=True)
    return db


def _seed_editorial_draft(tmp_path: Path, *, status: str = "generated"):
    db = _seed_paper_with_insight(tmp_path)
    draft = db.upsert_editorial_draft(
        paper_id=1,
        platform="bilibili",
        title="稀疏场先验如何让 3D 开放词汇理解更稳",
        hook="更少提示词，依然能把三维场景讲清楚。",
        markdown_content="# 稀疏场先验如何让 3D 开放词汇理解更稳\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-26" / "bilibili-2404-01812.md"),
    )

    if status == "in_review":
        draft = db.review_editorial_draft(draft.draft_id, actor="reviewer")
    elif status == "approved":
        db.review_editorial_draft(draft.draft_id, actor="reviewer")
        draft = db.approve_editorial_draft(draft.draft_id, actor="reviewer")
    elif status == "rejected":
        db.review_editorial_draft(draft.draft_id, actor="reviewer")
        draft = db.reject_editorial_draft(draft.draft_id, actor="reviewer", note="needs work")

    return db, draft


def test_health_endpoint_returns_http_api_envelope():
    client = ASGITestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["dataSource"] == "http"
    assert payload["meta"]["schemaVersion"] == "2026-04-27"
    assert payload["data"] == {"status": "ok"}


def test_list_papers_returns_contract_shaped_items(tmp_path):
    _seed_paper_with_insight(tmp_path)
    client = _make_client(tmp_path)

    response = client.get("/papers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["dataSource"] == "http"
    assert payload["data"]["total"] == 1
    assert payload["data"]["appliedQuery"] == ""
    item = payload["data"]["items"][0]
    assert item["paper"]["title"] == "Sparse Field Priors"
    assert item["paper"]["paperId"] >= 1
    assert item["insight"]["summaryShort"] == "Short summary."
    assert item["insight"]["confidenceScore"] == 0.91
    # 占位标记被透传到列表预览，前端据此显示徽标。
    assert item["insight"]["isPlaceholder"] is True
    assert item["notificationSummary"] == {
        "totalAttempts": 1,
        "latestStatus": "delivered",
        "lastSentAt": item["notificationSummary"]["lastSentAt"],
    }
    assert item["editorialDraftCount"] == 0


def test_list_papers_only_loads_page_scoped_relations_to_avoid_n_plus_one(tmp_path):
    """旧实现对 insights/notifications/drafts 三张表都做全表 SELECT。

    本测试种 50 篇论文，请求 limit=5；用 SQLAlchemy event 钩 SELECT 数量，
    断言每张关联表的 SELECT 都只命中当前页 paper_id（即 ``IN (...)`` 子句
    只包含 5 个 id），从而避免随论文增多而 OOM。
    """
    from sqlalchemy import event
    from app.storage import Database

    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()

    for i in range(50):
        paper = db.upsert_paper(_build_paper(source_paper_id=f"id-{i:03d}", title=f"Paper {i}"))
        if i % 7 == 0:
            db.upsert_paper_insight(
                paper_id=paper.paper_id,
                insight=PaperInsightRecord(
                    summary_short=f"short {i}",
                    summary_long=f"long {i}",
                ),
            )
        if i % 11 == 0:
            db.record_notification_attempt(destination="feishu", paper=paper, success=True)

    captured: list[str] = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def _capture(conn, cursor, statement, parameters, context, executemany):
        captured.append(statement)

    client = _make_client(tmp_path)
    response = client.get("/papers?limit=5")
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 5

    relation_selects = [
        sql for sql in captured
        if any(token in sql for token in ("paper_insights", "notifications", "editorial_drafts"))
    ]
    # 每张关联表至多 1 次 SELECT（带 IN(?,?,...,?) 限制到当前页 id）；
    # 旧实现会出现不带 WHERE 的全表 SELECT。
    for sql in relation_selects:
        assert "IN (" in sql or "in (" in sql, f"unexpected un-bounded select: {sql!r}"


def test_list_paper_insights_returns_full_insight_records(tmp_path):
    _seed_paper_with_insight(tmp_path)
    client = _make_client(tmp_path)

    response = client.get("/papers/insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] == 1
    insight = payload["data"]["items"][0]
    assert insight["summaryShort"] == "Short summary."
    assert insight["summaryLong"] == "Long summary."
    assert insight["noveltyPoints"] == ["novel point"]
    assert insight["limitations"] == ["limitation"]
    assert insight["applications"] == ["application"]
    assert insight["confidenceScore"] == 0.91


def test_get_paper_detail_returns_paper_insight_notifications_and_drafts(tmp_path):
    _, draft = _seed_editorial_draft(tmp_path)
    client = _make_client(tmp_path)

    response = client.get("/papers/1")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["paper"]["paperId"] == 1
    assert payload["insight"]["summaryLong"] == "Long summary."
    assert payload["notifications"][0]["destination"] == "feishu"
    assert payload["drafts"][0]["draftId"] == draft.draft_id
    assert payload["drafts"][0]["platform"] == "bilibili"


def test_list_papers_supports_search_filters_and_pagination(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    first = db.upsert_paper(_build_paper("2404.01812", "Sparse Field Priors"))
    second = db.upsert_paper(_build_paper("2404.99999", "Dense Video Reasoning"))
    db.upsert_paper_insight(
        paper_id=first.paper_id,
        insight=PaperInsightRecord(
            summary_short="Short summary.",
            summary_long="Long summary.",
            novelty_points=["novel point"],
            limitations=["limitation"],
            applications=["application"],
            confidence_score=0.91,
        ),
    )
    db.upsert_editorial_draft(
        paper_id=second.paper_id,
        platform="wechat",
        title="Dense Video Reasoning title",
        hook="hook",
        markdown_content="# draft\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-26" / "wechat-2404-99999.md"),
    )
    client = _make_client(tmp_path)

    response = client.get("/papers", params={"q": "dense", "hasDraft": "true", "limit": 1, "offset": 0})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["appliedQuery"] == "dense"
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["paper"]["title"] == "Dense Video Reasoning"


def test_list_editorial_drafts_reads_database_backed_drafts(tmp_path):
    _seed_editorial_draft(tmp_path)
    client = _make_client(tmp_path)

    response = client.get("/drafts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] == 1
    draft = payload["data"]["items"][0]
    assert draft["paperId"] == 1
    assert draft["platform"] == "bilibili"
    assert draft["status"] == "generated"
    assert draft["title"] == "稀疏场先验如何让 3D 开放词汇理解更稳"
    assert draft["hook"] == "更少提示词，依然能把三维场景讲清楚。"
    assert draft["outputPath"].endswith("bilibili-2404-01812.md")


def test_editorial_draft_detail_returns_markdown_and_paper_context(tmp_path):
    _, draft = _seed_editorial_draft(tmp_path, status="in_review")
    client = _make_client(tmp_path)

    response = client.get(f"/drafts/{draft.draft_id}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["draftId"] == draft.draft_id
    assert payload["status"] == "in_review"
    assert payload["markdownContent"] == "# 稀疏场先验如何让 3D 开放词汇理解更稳\n"
    assert payload["paper"]["paperId"] == 1
    assert payload["paper"]["title"] == "Sparse Field Priors"


def test_editorial_draft_actions_persist_assignment_and_status(tmp_path):
    _, draft = _seed_editorial_draft(tmp_path)
    client = _make_client(tmp_path)

    assign_response = client.post(
        f"/drafts/{draft.draft_id}/assign",
        json={"assignee": "alice", "actor": "lead"},
    )
    review_response = client.post(
        f"/drafts/{draft.draft_id}/review",
        json={"actor": "reviewer", "note": "start review"},
    )
    approve_response = client.post(
        f"/drafts/{draft.draft_id}/approve",
        json={"actor": "reviewer", "note": "ship it"},
    )

    assert assign_response.status_code == 200
    assert review_response.status_code == 200
    assert approve_response.status_code == 200
    assert assign_response.json()["data"]["assignee"] == "alice"
    assert review_response.json()["data"]["status"] == "in_review"
    assert approve_response.json()["data"]["status"] == "approved"


def test_editorial_draft_actions_reject_illegal_transition(tmp_path):
    _, draft = _seed_editorial_draft(tmp_path)
    client = _make_client(tmp_path)

    response = client.post(
        f"/drafts/{draft.draft_id}/approve",
        json={"actor": "reviewer"},
    )

    assert response.status_code == 409
    assert "illegal transition" in response.json()["detail"]


def test_editorial_draft_actions_return_404_for_missing_draft(tmp_path):
    _seed_paper_with_insight(tmp_path)
    client = _make_client(tmp_path)

    response = client.post(
        "/drafts/draft-missing/approve",
        json={"actor": "reviewer"},
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_editorial_draft_export_requires_approved_status_and_records_audit(tmp_path):
    _, draft = _seed_editorial_draft(tmp_path)
    client = _make_client(tmp_path)

    rejected_response = client.post(
        f"/drafts/{draft.draft_id}/export",
        json={},
    )

    assert rejected_response.status_code == 409
    assert "approved" in rejected_response.json()["detail"]

    client.post(f"/drafts/{draft.draft_id}/review", json={})
    client.post(f"/drafts/{draft.draft_id}/approve", json={})
    exported_response = client.post(
        f"/drafts/{draft.draft_id}/export",
        json={},
    )

    assert exported_response.status_code == 200
    export_payload = exported_response.json()["data"]
    assert export_payload["success"] is True
    assert export_payload["draftId"] == draft.draft_id
    assert export_payload["destinationPath"].endswith("bilibili-2404-01812.md")
    assert export_payload["exportedBy"].startswith("api:")

    exports_response = client.get("/exports")
    assert exports_response.status_code == 200
    exports = exports_response.json()["data"]["items"]
    assert len(exports) == 2
    assert exports[-1]["success"] is True
    assert exports[-1]["exportedBy"].startswith("api:")



def test_editorial_draft_export_returns_latest_audit_record_for_same_destination(tmp_path):
    db, draft = _seed_editorial_draft(tmp_path, status="approved")
    client = _make_client(tmp_path)

    first = client.post(
        f"/drafts/{draft.draft_id}/export",
        json={},
    )
    assert first.status_code == 200

    with db._session() as session:
        persisted = session.get(type(draft), draft.draft_id)
        persisted.status = "approved"
        session.commit()

    second = client.post(
        f"/drafts/{draft.draft_id}/export",
        json={},
    )

    assert second.status_code == 200
    first_payload = first.json()["data"]
    second_payload = second.json()["data"]
    assert second_payload["exportId"] > first_payload["exportId"]
    assert second_payload["exportedBy"].startswith("api:")
    assert second_payload["destinationPath"] == first_payload["destinationPath"]
