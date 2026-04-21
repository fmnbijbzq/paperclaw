from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.notification_pipeline import run_notification_cycle
from app.schemas import PaperRecord
from app.storage import Database


def _build_paper(source_paper_id: str, title: str) -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        title=title,
        authors=["Alice"],
        paper_url=f"https://arxiv.org/abs/{source_paper_id}",
        dedup_key=f"{title.lower()}|alice|2024",
        raw_payload={"id": source_paper_id},
    )


class FakeNotifier:
    def __init__(self, *, fail_titles: set[str] | None = None, max_items: int | None = None) -> None:
        self.fail_titles = fail_titles or set()
        self.max_items = max_items
        self.sent_batches: list[list[str]] = []

    def send_combined(self, papers):
        limited = list(papers)
        if self.max_items is not None:
            limited = limited[: self.max_items]
        titles = [paper.title for paper in limited]
        self.sent_batches.append(titles)
        failing = self.fail_titles.intersection(titles)
        if failing:
            raise RuntimeError(f"failed batch: {sorted(failing)!r}")
        return {"StatusCode": 0}


def test_run_notification_cycle_marks_successful_combined_batch(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    db.upsert_paper(_build_paper("1111.1111", "First Paper"))
    db.upsert_paper(_build_paper("2222.2222", "Second Paper"))
    notifier = FakeNotifier()

    summary = run_notification_cycle(
        database_url=database_url,
        notifier=notifier,
        batch_size=2,
        destination="feishu",
    )

    attempts = db.list_notifications(destination="feishu")
    pending = db.list_unnotified_papers(destination="feishu", limit=10)

    assert summary.attempted == 2
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert notifier.sent_batches == [["First Paper", "Second Paper"]]
    assert len(attempts) == 2
    assert all(attempt.success is True for attempt in attempts)
    assert pending == []


def test_run_notification_cycle_records_failed_combined_batch_and_retries_next_time(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    db.upsert_paper(_build_paper("1111.1111", "First Paper"))
    notifier = FakeNotifier(fail_titles={"First Paper"})

    first = run_notification_cycle(
        database_url=database_url,
        notifier=notifier,
        batch_size=1,
        destination="feishu",
    )
    second = run_notification_cycle(
        database_url=database_url,
        notifier=FakeNotifier(),
        batch_size=1,
        destination="feishu",
    )

    attempts = db.list_notifications(destination="feishu")

    assert first.attempted == 1
    assert first.succeeded == 0
    assert first.failed == 1
    assert second.succeeded == 1
    assert [attempt.success for attempt in attempts] == [False, True]


def test_run_notification_cycle_uses_batch_size_limit(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    db.upsert_paper(_build_paper("1111.1111", "First Paper"))
    db.upsert_paper(_build_paper("2222.2222", "Second Paper"))
    notifier = FakeNotifier()

    summary = run_notification_cycle(
        database_url=database_url,
        notifier=notifier,
        batch_size=1,
        destination="feishu",
    )

    attempts = db.list_notifications(destination="feishu")
    pending = db.list_unnotified_papers(destination="feishu", limit=10)

    assert summary.attempted == 1
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert notifier.sent_batches == [["First Paper"]]
    assert [attempt.success for attempt in attempts] == [True]
    assert [paper.title for paper in pending] == ["Second Paper"]


def test_run_notification_cycle_only_marks_actually_sent_papers_successful(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    db.upsert_paper(_build_paper("1111.1111", "First Paper"))
    db.upsert_paper(_build_paper("2222.2222", "Second Paper"))
    notifier = FakeNotifier(max_items=1)

    summary = run_notification_cycle(
        database_url=database_url,
        notifier=notifier,
        batch_size=2,
        destination="feishu",
    )

    attempts = db.list_notifications(destination="feishu")
    pending = db.list_unnotified_papers(destination="feishu", limit=10)

    assert summary.attempted == 1
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert notifier.sent_batches == [["First Paper"]]
    assert [attempt.paper_id for attempt in attempts] == [1]
    assert [paper.title for paper in pending] == ["Second Paper"]
