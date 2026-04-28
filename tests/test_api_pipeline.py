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
from app.summarization.schemas import PaperInsightRecord


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


def _seed_pipeline_state(tmp_path: Path) -> None:
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    paper1 = db.upsert_paper(_build_paper("a1", "Alpha Paper", "arxiv"))
    paper2 = db.upsert_paper(_build_paper("o1", "Omega Paper", "openreview"))

    db.upsert_paper_insight(
        paper_id=paper1.paper_id,
        insight=PaperInsightRecord(
            summary_short="short",
            summary_long="long",
            novelty_points=["novel"],
            limitations=["limit"],
            applications=["apply"],
            confidence_score=0.8,
        ),
    )
    db.record_notification_attempt(destination="feishu", paper=paper1, success=True)

    db.start_crawl_run("arxiv")
    arxiv_run = db.start_crawl_run("arxiv")
    db.finish_crawl_run(arxiv_run.run_id, status="success", fetched_count=12, new_count=3)

    openreview_run = db.start_crawl_run("openreview")
    db.finish_crawl_run(openreview_run.run_id, status="failed", fetched_count=5, new_count=1, error_message="timeout")

    db.upsert_editorial_draft(
        paper_id=paper1.paper_id,
        platform="bilibili",
        title="Alpha 标题",
        hook="Alpha Hook",
        markdown_content="# Alpha 标题\n\n> Hook: Alpha Hook\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-26" / "bilibili-alpha.md"),
    )


def test_pipeline_summary_returns_metrics_stages_and_source_health(tmp_path):
    _seed_pipeline_state(tmp_path)
    client = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path/'papers.db'}",
            editorial_root=tmp_path / "outputs" / "editorial",
        )
    )

    response = client.get("/pipeline/summary")

    assert response.status_code == 200
    payload = response.json()
    metrics = payload["data"]["metrics"]
    assert metrics["totalPapers"] == 2
    assert metrics["papersWithInsights"] == 1
    assert metrics["pendingNotifications"] == 1
    assert metrics["editorialDrafts"] == 1

    stages = payload["data"]["stages"]
    stage_ids = {stage["stageId"] for stage in stages}
    assert {"fetch", "normalize", "store", "insight", "editorial", "export"}.issubset(stage_ids)

    source_health = payload["data"]["sourceHealth"]
    sources = {item["source"]: item for item in source_health}
    assert sources["arxiv"]["status"] == "healthy"
    assert sources["arxiv"]["fetchedCount"] == 12
    assert sources["arxiv"]["newCount"] == 3
    assert sources["openreview"]["status"] == "degraded"
    assert sources["openreview"]["fetchedCount"] == 5


def test_pipeline_summary_counts_database_backed_drafts_without_filesystem_scan(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("db-only", "Database Draft Paper", "arxiv"))
    db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="DB only draft",
        hook="hook",
        markdown_content="# db draft\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-26" / "bilibili-db-only.md"),
    )
    stray_file = tmp_path / "outputs" / "editorial" / "2026-04-26" / "stray-only.md"
    stray_file.parent.mkdir(parents=True, exist_ok=True)
    stray_file.write_text("# stray file\n", encoding="utf-8")

    client = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path/'papers.db'}",
            editorial_root=tmp_path / "outputs" / "editorial",
        )
    )

    response = client.get("/pipeline/summary")

    assert response.status_code == 200
    assert response.json()["data"]["metrics"]["editorialDrafts"] == 1


def test_create_app_raises_when_repo_dotenv_exists_but_required_settings_are_invalid(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    dotenv_path = project_root / ".env"
    original = dotenv_path.read_text(encoding="utf-8") if dotenv_path.exists() else None
    dotenv_path.write_text("FEISHU_BOT_WEBHOOK=https://example.invalid/webhook\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        try:
            create_app()
        except Exception as exc:
            assert exc.__class__.__name__ == "ValidationError"
        else:
            raise AssertionError("create_app() should fail when .env exists but DATABASE_URL is missing")
    finally:
        if original is None:
            dotenv_path.unlink(missing_ok=True)
        else:
            dotenv_path.write_text(original, encoding="utf-8")
