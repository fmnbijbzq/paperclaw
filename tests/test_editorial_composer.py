from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.editorial.composer import EditorialComposer
from app.schemas import PaperRecord
from app.summarization.schemas import PaperInsightRecord


def _build_paper() -> PaperRecord:
    return PaperRecord(
        source="demo",
        source_paper_id="demo-1",
        title="Vision Demo Paper",
        abstract="A compact abstract.",
        full_text="A longer full text for deterministic drafting.",
        authors=["Alice"],
        paper_url="https://example.test/paper/1",
        venue="CVPR 2026",
    )


def _build_insight() -> PaperInsightRecord:
    return PaperInsightRecord(
        summary_short="提出了更稳定的训练与推理策略。",
        summary_long="该论文围绕视觉理解任务提出统一的训练框架。",
        novelty_points=["统一训练范式", "更强鲁棒性", "更低推理成本"],
        limitations=["需要更大规模数据进一步验证"],
        applications=["视觉检索", "视频理解", "内容生产辅助"],
        confidence_score=0.82,
    )


def test_editorial_composer_generates_three_platform_drafts():
    templates_dir = Path(__file__).resolve().parents[1] / "app" / "editorial" / "templates"
    composer = EditorialComposer(str(templates_dir))

    paper = _build_paper()
    insight = _build_insight()

    bilibili = composer.compose(platform="bilibili", paper=paper, insight=insight)
    xiaohongshu = composer.compose(platform="xiaohongshu", paper=paper, insight=insight)
    douyin = composer.compose(platform="douyin", paper=paper, insight=insight)

    assert bilibili.title
    assert bilibili.body
    assert bilibili.tags

    assert xiaohongshu.title
    assert xiaohongshu.body
    assert xiaohongshu.tags

    assert douyin.title
    assert douyin.body
    assert douyin.tags


def test_editorial_composer_raises_for_unknown_platform():
    templates_dir = Path(__file__).resolve().parents[1] / "app" / "editorial" / "templates"
    composer = EditorialComposer(str(templates_dir))

    paper = _build_paper()
    insight = _build_insight()

    try:
        composer.compose(platform="unknown", paper=paper, insight=insight)
    except ValueError as exc:
        assert "Unsupported platform" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported platform")
