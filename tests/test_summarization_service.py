from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas import PaperRecord
from app.summarization.service import SummarizationService


def _paper(*, title: str, abstract: str | None, full_text: str | None) -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id="1234.5678",
        title=title,
        abstract=abstract,
        full_text=full_text,
        authors=["Alice"],
        paper_url="https://arxiv.org/abs/1234.5678",
    )


def test_summarization_service_returns_structured_fields():
    service = SummarizationService()

    insight = service.generate(
        _paper(
            title="Vision Foundation Model",
            abstract="We propose a new unified training strategy.",
            full_text="This paper proposes a unified strategy for image and video understanding.",
        )
    )

    assert insight.summary_short
    assert insight.summary_long
    assert len(insight.novelty_points) >= 3
    assert len(insight.limitations) >= 1
    assert len(insight.applications) >= 1
    # 模板 service 不输出真实置信度，前端据此显示"未启用 AI 摘要"徽标。
    assert insight.confidence_score is None
    assert insight.is_placeholder is True
    assert insight.generator == "template-v1"


def test_summarization_service_falls_back_without_full_text():
    service = SummarizationService()

    insight = service.generate(
        _paper(
            title="Only Abstract Paper",
            abstract="Abstract only content.",
            full_text=None,
        )
    )

    assert "Only Abstract Paper" in insight.summary_long
    assert any("未获得完整正文" in item for item in insight.limitations)


def test_summarization_service_handles_missing_abstract_and_full_text():
    service = SummarizationService()

    insight = service.generate(
        _paper(
            title="Title Only Paper",
            abstract=None,
            full_text=None,
        )
    )

    assert "Title Only Paper" in insight.summary_short
    # 模板 service 不再硬编码 confidence；占位 insight 的 confidence_score 留空。
    assert insight.confidence_score is None
    assert insight.is_placeholder is True
