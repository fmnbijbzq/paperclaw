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
