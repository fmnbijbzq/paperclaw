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
                abstract="Abstract text",
                full_text="Full text content",
                authors=["Alice"],
                paper_url="https://arxiv.org/abs/1234.5678",
            )
        ]


class FailingSource:
    name = "broken"

    def fetch(self):
        raise RuntimeError("boom")


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
    assert summary.total_insighted == 1


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


def test_run_pipeline_continues_after_one_source_fails(tmp_path):
    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FailingSource(), FakeSource()],
        notifier=None,
    )

    assert summary.total_fetched == 1
    assert summary.total_new == 1
    assert summary.per_source["broken"]["status"] == "failed"
    assert summary.per_source["arxiv"]["status"] == "success"
    assert summary.failed_sources == ["broken"]
    assert summary.has_failures is True


def test_run_pipeline_continues_when_insight_generation_fails(tmp_path, monkeypatch):
    class BrokenSummarizer:
        def generate(self, paper):
            raise RuntimeError("insight failed")

    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FakeSource()],
        notifier=None,
        summarizer=BrokenSummarizer(),
    )

    assert summary.total_new == 1
    assert summary.total_insighted == 0


def test_run_pipeline_skips_resummarization_when_non_placeholder_insight_exists(tmp_path):
    """切到真实 LLM 后，重复 run 不应对已有 insight 反复扣费。"""
    from app.summarization.schemas import PaperInsightRecord
    from app.summarization.service import SummarizationService

    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    class CountingSummarizer(SummarizationService):
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, paper):
            self.calls += 1
            # 模拟真实 LLM 输出：is_placeholder=False
            return PaperInsightRecord(
                summary_short="real",
                summary_long="real long",
                novelty_points=["a", "b", "c"],
                limitations=["x"],
                applications=["y"],
                confidence_score=0.9,
                is_placeholder=False,
                generator="llm-v1",
            )

    summarizer = CountingSummarizer()

    first = run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None, summarizer=summarizer)
    second = run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None, summarizer=summarizer)

    assert first.total_insighted == 1
    assert summarizer.calls == 1
    # 第二次 run 跳过了 summarize：fetched=1（重复抓到），insighted=0。
    assert second.total_fetched == 1
    assert second.total_insighted == 0
    assert summarizer.calls == 1


def test_run_pipeline_force_resummarize_overrides_existing_insight(tmp_path):
    """模型升级回填场景：开启 force 后即使存在真实 insight 也会重新生成。"""
    from app.summarization.schemas import PaperInsightRecord
    from app.summarization.service import SummarizationService

    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    class CountingSummarizer(SummarizationService):
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, paper):
            self.calls += 1
            return PaperInsightRecord(
                summary_short=f"call {self.calls}",
                summary_long="long",
                is_placeholder=False,
                generator="llm-v1",
            )

    summarizer = CountingSummarizer()
    run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None, summarizer=summarizer)
    assert summarizer.calls == 1

    run_pipeline(
        database_url=database_url,
        sources=[FakeSource()],
        notifier=None,
        summarizer=summarizer,
        force_resummarize=True,
    )
    assert summarizer.calls == 2


def test_run_pipeline_replaces_placeholder_insight_with_real_output(tmp_path):
    """旧数据是模板占位，新 service 切到真实 LLM 时应当被覆盖（不算重复扣费）。"""
    from app.summarization.schemas import PaperInsightRecord
    from app.summarization.service import SummarizationService

    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    # 第一次：默认模板 service，写入 is_placeholder=True
    placeholder_summarizer = SummarizationService()
    run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None, summarizer=placeholder_summarizer)

    db = Database(database_url)
    paper = db.list_papers_with_insights(limit=1)[0][0]
    insight = db.get_paper_insight(paper_id=paper.paper_id)
    assert insight.is_placeholder is True

    # 第二次：真实 LLM service，应当覆盖
    class RealSummarizer:
        calls = 0

        def generate(self, paper_record):
            RealSummarizer.calls += 1
            return PaperInsightRecord(
                summary_short="real",
                summary_long="real long",
                is_placeholder=False,
                generator="llm-v1",
                confidence_score=0.93,
            )

    run_pipeline(database_url=database_url, sources=[FakeSource()], notifier=None, summarizer=RealSummarizer())
    assert RealSummarizer.calls == 1

    refreshed = db.get_paper_insight(paper_id=paper.paper_id)
    assert refreshed.is_placeholder is False
    assert refreshed.generator == "llm-v1"
    assert refreshed.confidence_score == 0.93


# ---------------------------------------------------------------------------
# Per-paper error isolation + failure-queue retry
# ---------------------------------------------------------------------------


class _OneGoodOneBadSource:
    """First record is fine, second triggers a writable upsert error mid-loop."""
    name = "arxiv"

    def fetch(self):
        return [
            PaperRecord(
                source="arxiv",
                source_paper_id="good-1",
                title="Good Paper",
                abstract="ok",
                authors=["Alice"],
                paper_url="https://arxiv.org/abs/good-1",
            ),
            PaperRecord(
                source="arxiv",
                source_paper_id="bad-2",
                title="Bad Paper",
                abstract="will explode at upsert time",
                # \ud835 is an unpaired UTF-16 surrogate. SQLite UTF-8 write
                # raises UnicodeEncodeError on it. We feed it directly into
                # PaperRecord.full_text (bypassing TextExtractor's surrogate
                # cleaner) so the per-paper try/except path is exercised
                # against a real SQLite encoding error.
                full_text="text with \ud835 surrogate",
                authors=["Bob"],
                paper_url="https://arxiv.org/abs/bad-2",
            ),
            PaperRecord(
                source="arxiv",
                source_paper_id="good-3",
                title="Third Paper",
                abstract="comes after the bad one",
                authors=["Carol"],
                paper_url="https://arxiv.org/abs/good-3",
            ),
        ]


def test_one_bad_paper_does_not_abort_the_source_run(tmp_path):
    """Spec acceptance: a single paper failing must not flip CrawlRun to
    failed, must not skip subsequent papers, and must record the failure."""
    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    summary = run_pipeline(
        database_url=database_url,
        sources=[_OneGoodOneBadSource()],
        notifier=None,
    )

    db = Database(database_url)

    # The two good papers got in.
    assert db.count_papers() == 2
    # CrawlRun for arxiv is success because source.fetch() worked.
    runs = db.list_crawl_runs(source="arxiv", limit=10)
    assert runs[0].status == "success"
    assert runs[0].fetched_count == 3
    assert runs[0].new_count == 2
    # The bad paper sits in the failure queue.
    pending = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending) == 1
    assert pending[0].source_paper_id == "bad-2"
    assert pending[0].attempts == 1
    # And the summary surfaces the per-source failure count.
    assert summary.per_source["arxiv"]["failed_papers"] == 1
    assert summary.per_source["arxiv"]["status"] == "success"


class _NoOpSource:
    """Fetches nothing - used to test the retry path independently of new fetches."""
    name = "arxiv"

    def fetch(self):
        return []


def test_pending_failure_is_retried_and_resolved_on_next_run(tmp_path):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    # Round 1: the bad paper enters the failure queue.
    run_pipeline(
        database_url=database_url,
        sources=[_OneGoodOneBadSource()],
        notifier=None,
    )

    db = Database(database_url)
    pending_before = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending_before) == 1
    bad_id = pending_before[0].failure_id

    # Simulate the surrogate fix being applied to the queued payload (in
    # real life the surrogate fix in extractor would prevent the failure
    # ever happening; this test isolates the retry logic itself).
    from app.enrichment.extractor import _strip_unpaired_surrogates
    from app.models import PaperFetchFailure
    with db._session() as session:
        row = session.get(PaperFetchFailure, bad_id)
        payload = dict(row.raw_payload)
        payload["full_text"] = _strip_unpaired_surrogates(payload["full_text"])
        row.raw_payload = payload
        session.commit()

    # No new fetch this round; only the retry path should fire.
    run_pipeline(
        database_url=database_url,
        sources=[_NoOpSource()],
        notifier=None,
    )

    pending_after = db.list_pending_failures(source="arxiv", limit=10)
    assert pending_after == []
    # The previously-failed paper is now in the papers table.
    assert db.count_papers() == 3
