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
    assert db.table_exists("editorial_drafts")
    assert db.table_exists("export_records")


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


def test_list_papers_with_insights_where_no_draft_excludes_already_drafted_papers(tmp_path):
    """The dashboard editorial stage uses where_no_draft=True so re-triggering
    does not regenerate (and clobber the review state of) existing drafts."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    drafted = db.upsert_paper(_build_paper("2000.0001", "Already Drafted"))
    fresh = db.upsert_paper(_build_paper("2000.0002", "Awaiting Draft"))
    for paper in (drafted, fresh):
        db.upsert_paper_insight(
            paper_id=paper.paper_id,
            insight=PaperInsightRecord(
                summary_short="s",
                summary_long="l",
                novelty_points=["n"],
                limitations=[],
                applications=[],
                confidence_score=0.5,
            ),
        )
    db.upsert_editorial_draft(
        paper_id=drafted.paper_id,
        platform="bilibili",
        title="Existing",
        hook="hook",
        markdown_content="# existing\n",
        output_path=str(tmp_path / "outputs" / "bilibili-existing.md"),
    )

    # Default (False) keeps current behaviour — both papers come back.
    all_rows = db.list_papers_with_insights(limit=10)
    assert {p.title for p, _ in all_rows} == {"Already Drafted", "Awaiting Draft"}

    # where_no_draft=True excludes any paper that already has any draft row.
    fresh_rows = db.list_papers_with_insights(limit=10, where_no_draft=True)
    assert [p.title for p, _ in fresh_rows] == ["Awaiting Draft"]


def test_upsert_editorial_draft_reuses_single_row_and_resets_status_on_regeneration(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("4444.4444", "Draft Paper"))

    created = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="First Title",
        hook="First Hook",
        markdown_content="# first\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-28" / "bilibili-draft.md"),
    )
    db.review_editorial_draft(created.draft_id, actor="reviewer")
    db.approve_editorial_draft(created.draft_id, actor="reviewer")

    updated = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="Second Title",
        hook="Second Hook",
        markdown_content="# second\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-29" / "bilibili-draft.md"),
    )

    drafts = db.list_editorial_drafts()

    assert created.draft_id == updated.draft_id
    assert len(drafts) == 1
    assert updated.status == "generated"
    assert updated.title == "Second Title"
    assert updated.output_path.endswith("2026-04-29/bilibili-draft.md")


def test_editorial_draft_state_machine_rejects_illegal_transitions(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("5555.5555", "State Paper"))
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="xiaohongshu",
        title="State Title",
        hook="State Hook",
        markdown_content="# state\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-28" / "xiaohongshu-state.md"),
    )

    try:
        db.approve_editorial_draft(draft.draft_id, actor="reviewer")
    except ValueError as exc:
        assert "illegal transition" in str(exc)
    else:
        raise AssertionError("expected illegal transition to be rejected")

    reviewed = db.review_editorial_draft(draft.draft_id, actor="reviewer")
    approved = db.approve_editorial_draft(draft.draft_id, actor="reviewer")

    assert reviewed.status == "in_review"
    assert approved.status == "approved"


def test_record_export_success_transitions_approved_draft_and_persists_audit_row(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("6666.6666", "Export Paper"))
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="douyin",
        title="Export Title",
        hook="Export Hook",
        markdown_content="# export\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "2026-04-28" / "douyin-export.md"),
    )
    db.review_editorial_draft(draft.draft_id, actor="reviewer")
    db.approve_editorial_draft(draft.draft_id, actor="reviewer")

    record = db.record_export_success(
        draft_id=draft.draft_id,
        exported_by="publisher",
        source_path=draft.output_path,
        destination_path=str(tmp_path / "outputs" / "exported" / "2026-04-28" / "douyin-export.md"),
    )

    stored = db.get_editorial_draft(draft.draft_id)
    records = db.list_export_records()

    assert stored is not None
    assert stored.status == "exported"
    assert record.success is True
    assert len(records) == 1
    assert records[0].draft_id == draft.draft_id


# ---------------------------------------------------------------------------
# paper_fetch_failures (failure queue)
# ---------------------------------------------------------------------------


def test_record_paper_failure_creates_row_with_attempts_one(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    failure = db.record_paper_failure(
        source="arxiv",
        record=_build_paper(),
        error_phase="upsert",
        error=ValueError("bang"),
    )

    assert failure.attempts == 1
    assert failure.source == "arxiv"
    assert failure.source_paper_id == "1234.5678"
    assert failure.error_phase == "upsert"
    assert "bang" in failure.error_message
    assert failure.resolved_at is None
    # raw_payload must carry the full record so a retry can replay without re-fetching
    assert failure.raw_payload["title"] == "Test Paper"
    assert failure.raw_payload["authors"] == ["Alice", "Bob"]


def test_record_paper_failure_is_idempotent_per_source_and_paper(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    db.record_paper_failure(
        source="arxiv",
        record=_build_paper(),
        error_phase="normalize",
        error=ValueError("first"),
    )
    second = db.record_paper_failure(
        source="arxiv",
        record=_build_paper(),
        error_phase="upsert",
        error=ValueError("second"),
    )

    assert second.attempts == 2
    assert second.error_phase == "upsert"
    assert "second" in second.error_message
    pending = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending) == 1


def test_list_pending_failures_excludes_resolved_and_exhausted(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    a = db.record_paper_failure(
        source="arxiv",
        record=_build_paper(source_paper_id="aa"),
        error_phase="upsert",
        error=ValueError("a"),
    )
    b = db.record_paper_failure(
        source="arxiv",
        record=_build_paper(source_paper_id="bb"),
        error_phase="upsert",
        error=ValueError("b"),
    )
    db.record_paper_failure(
        source="arxiv",
        record=_build_paper(source_paper_id="cc"),
        error_phase="upsert",
        error=ValueError("c"),
    )

    db.mark_failure_resolved(a.failure_id)
    # bump b past max_attempts (5)
    for _ in range(5):
        db.bump_failure_attempts(b.failure_id, error_phase="upsert", error=ValueError("again"))

    pending = db.list_pending_failures(source="arxiv", limit=10, max_attempts=5)
    pending_ids = {row.source_paper_id for row in pending}
    assert pending_ids == {"cc"}


def test_list_pending_failures_filters_by_source(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    db.record_paper_failure(
        source="arxiv",
        record=_build_paper(source_paper_id="a1"),
        error_phase="upsert",
        error=ValueError("x"),
    )
    db.record_paper_failure(
        source="openreview",
        record=PaperRecord(
            source="openreview",
            source_paper_id="o1",
            title="t",
            paper_url="https://openreview.net/forum?id=o1",
        ),
        error_phase="upsert",
        error=ValueError("y"),
    )

    arxiv_pending = db.list_pending_failures(source="arxiv", limit=10)
    or_pending = db.list_pending_failures(source="openreview", limit=10)
    assert {f.source_paper_id for f in arxiv_pending} == {"a1"}
    assert {f.source_paper_id for f in or_pending} == {"o1"}


def test_mark_failure_resolved_sets_resolved_at(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    failure = db.record_paper_failure(
        source="arxiv",
        record=_build_paper(),
        error_phase="upsert",
        error=ValueError("bang"),
    )
    assert failure.resolved_at is None

    resolved = db.mark_failure_resolved(failure.failure_id)
    assert resolved.resolved_at is not None
    assert db.list_pending_failures(source="arxiv", limit=10) == []
