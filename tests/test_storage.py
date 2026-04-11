from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas import PaperRecord
from app.storage import Database


def _build_paper(source_paper_id: str = "1234.5678", title: str = "Test Paper") -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        title=title,
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
