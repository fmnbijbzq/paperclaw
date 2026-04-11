from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.pipeline import run_pipeline
from app.schemas import PaperRecord
from app.storage import Database


class FakeSource:
    name = "arxiv"

    def fetch(self):
        return [
            PaperRecord(
                source="arxiv",
                source_paper_id="1234.5678",
                title="Vision Paper",
                authors=["Alice"],
                paper_url="https://arxiv.org/abs/1234.5678",
            )
        ]


def test_run_pipeline_inserts_and_returns_summary(tmp_path):
    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FakeSource()],
        notifier=None,
    )

    assert summary.total_new == 1
    assert summary.total_fetched == 1
    assert summary.total_notified == 0
    assert len(summary.new_papers) == 1
    assert summary.new_papers[0].dedup_key == "vision paper|alice"


def test_run_pipeline_is_idempotent_across_repeated_runs(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    first = run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None)
    second = run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None)

    db = Database(database_url)

    assert first.total_new == 1
    assert second.total_new == 0
    assert second.total_fetched == 1
    assert db.count_papers() == 1


def test_run_pipeline_does_not_use_global_counts_for_insert_detection(tmp_path, monkeypatch):
    def fail_count(self):
        raise AssertionError("count_papers should not be used for insert detection")

    monkeypatch.setattr(Database, "count_papers", fail_count)

    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FakeSource()],
        notifier=None,
    )

    assert summary.total_new == 1


def test_run_pipeline_does_not_send_notifications(tmp_path):
    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FakeSource()],
        notifier=None,
    )

    assert summary.total_new == 1
    assert summary.total_notified == 0
