from pathlib import Path
import sqlite3
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas import PaperRecord
from app.storage import Database
from app.summarization.schemas import PaperInsightRecord


def _build_paper(source_paper_id: str = "1234.5678", title: str = "Test Paper") -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        title=title,
        abstract="test abstract",
        full_text="test full text",
        authors=["Alice", "Bob"],
        paper_url=f"https://arxiv.org/abs/{source_paper_id}",
        dedup_key=f"{title.lower()}|alice|2024",
        raw_payload={"id": source_paper_id},
    )


def test_database_creates_tables(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")

    db.create_schema()

    assert db.table_exists("papers")
    assert db.table_exists("paper_versions")
    assert db.table_exists("crawl_runs")
    assert db.table_exists("notifications")


def test_upsert_paper_is_idempotent(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = _build_paper()

    first = db.upsert_paper(paper)
    second = db.upsert_paper(paper)

    assert first.paper_id == second.paper_id
    assert db.count_papers() == 1


def test_upsert_paper_with_status_reports_created_only_once(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = _build_paper()

    first = db.upsert_paper_with_status(paper)
    second = db.upsert_paper_with_status(paper)

    assert first.created is True
    assert second.created is False
    assert first.paper.paper_id == second.paper.paper_id


def test_list_unnotified_papers_excludes_notified_records(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    first = db.upsert_paper(_build_paper("1111.1111", "First Paper"))
    second = db.upsert_paper(_build_paper("2222.2222", "Second Paper"))

    pending_before = db.list_unnotified_papers(destination="feishu", limit=10)
    db.record_notification_attempt(destination="feishu", paper=first, success=True)
    pending_after = db.list_unnotified_papers(destination="feishu", limit=10)

    assert [paper.paper_id for paper in pending_before] == [first.paper_id, second.paper_id]
    assert [paper.paper_id for paper in pending_after] == [second.paper_id]


def test_failed_notification_attempt_keeps_paper_pending(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("1111.1111", "First Paper"))

    db.record_notification_attempt(
        destination="feishu",
        paper=paper,
        success=False,
        error_message="timeout",
    )

    pending = db.list_unnotified_papers(destination="feishu", limit=10)
    attempts = db.list_notifications(destination="feishu")

    assert [item.paper_id for item in pending] == [paper.paper_id]
    assert len(attempts) == 1
    assert attempts[0].success is False
    assert attempts[0].error_message == "timeout"


def test_crawl_run_lifecycle_persists_counts(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    crawl_run = db.start_crawl_run("arxiv")
    finished = db.finish_crawl_run(crawl_run.run_id, status="success", fetched_count=3, new_count=2)

    assert finished.status == "success"
    assert finished.fetched_count == 3
    assert finished.new_count == 2


def test_database_creates_missing_parent_directory_for_relative_sqlite_url(tmp_path, monkeypatch):
    working_dir = tmp_path / "workspace"
    working_dir.mkdir()
    monkeypatch.chdir(working_dir)

    db = Database("sqlite:///data/papers.db")

    db.create_schema()

    assert (working_dir / "data").is_dir()
    assert (working_dir / "data" / "papers.db").exists()


def test_create_schema_migrates_legacy_notifications_table(tmp_path):
    db_path = tmp_path / "papers.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE notifications (
                notification_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                destination VARCHAR(255) NOT NULL,
                paper_id INTEGER NOT NULL,
                sent_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = Database(f"sqlite:///{db_path}")

    db.create_schema()

    migrated = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(notifications)")}
    finally:
        migrated.close()

    assert "success" in columns
    assert "error_message" in columns


def test_create_schema_migrates_full_text_columns_for_legacy_tables(tmp_path):
    db_path = tmp_path / "papers.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE papers (
                paper_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                source VARCHAR(50) NOT NULL,
                source_paper_id VARCHAR(255) NOT NULL,
                dedup_key VARCHAR(500),
                title VARCHAR(500) NOT NULL,
                abstract TEXT,
                authors JSON,
                paper_url VARCHAR(1000) NOT NULL,
                pdf_url VARCHAR(1000),
                venue VARCHAR(255),
                categories JSON,
                published_at DATETIME,
                updated_at_source DATETIME,
                raw_payload JSON,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE paper_versions (
                version_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                title VARCHAR(500) NOT NULL,
                abstract TEXT,
                authors JSON,
                categories JSON,
                paper_url VARCHAR(1000) NOT NULL,
                pdf_url VARCHAR(1000),
                venue VARCHAR(255),
                published_at DATETIME,
                updated_at_source DATETIME,
                raw_payload JSON,
                created_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = Database(f"sqlite:///{db_path}")
    db.create_schema()

    migrated = sqlite3.connect(db_path)
    try:
        paper_columns = {row[1] for row in migrated.execute("PRAGMA table_info(papers)")}
        version_columns = {row[1] for row in migrated.execute("PRAGMA table_info(paper_versions)")}
    finally:
        migrated.close()

    assert "full_text" in paper_columns
    assert "full_text" in version_columns


def test_upsert_paper_insight_creates_and_updates_single_row(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("3333.3333", "Insight Paper"))

    created = db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="short",
            summary_long="long",
            novelty_points=["n1"],
            limitations=["l1"],
            applications=["a1"],
            confidence_score=0.8,
        ),
    )
    updated = db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="short2",
            summary_long="long2",
            novelty_points=["n2"],
            limitations=["l2"],
            applications=["a2"],
            confidence_score=0.9,
        ),
    )

    stored = db.get_paper_insight(paper_id=paper.paper_id)

    assert created.insight_id == updated.insight_id
    assert stored is not None
    assert stored.summary_short == "short2"
    assert stored.novelty_points == ["n2"]
    assert stored.confidence_score == 0.9


def test_list_papers_with_insights_returns_latest_papers_first(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    paper1 = db.upsert_paper(_build_paper("1000.0001", "Older Paper"))
    paper2 = db.upsert_paper(_build_paper("1000.0002", "Newer Paper"))

    db.upsert_paper_insight(
        paper_id=paper1.paper_id,
        insight=PaperInsightRecord(
            summary_short="older short",
            summary_long="older long",
            novelty_points=["o1"],
            limitations=[],
            applications=[],
            confidence_score=0.7,
        ),
    )
    db.upsert_paper_insight(
        paper_id=paper2.paper_id,
        insight=PaperInsightRecord(
            summary_short="newer short",
            summary_long="newer long",
            novelty_points=["n1"],
            limitations=[],
            applications=[],
            confidence_score=0.8,
        ),
    )

    rows = db.list_papers_with_insights(limit=10)

    assert [paper.title for paper, _ in rows] == ["Newer Paper", "Older Paper"]
    assert rows[0][1].summary_short == "newer short"
    assert rows[1][1].summary_short == "older short"


def test_list_papers_with_insights_skips_papers_without_insights(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    paper = db.upsert_paper(_build_paper("1000.0003", "No Insight Paper"))
    db.upsert_paper(_build_paper("1000.0004", "Another No Insight Paper"))
    insight_paper = db.upsert_paper(_build_paper("1000.0005", "Insightful Paper"))

    db.upsert_paper_insight(
        paper_id=insight_paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="insight short",
            summary_long="insight long",
            novelty_points=["i1"],
            limitations=[],
            applications=[],
            confidence_score=0.85,
        ),
    )

    rows = db.list_papers_with_insights(limit=10)

    assert [item.title for item, _ in rows] == ["Insightful Paper"]
    assert all(item.paper_id != paper.paper_id for item, _ in rows)
