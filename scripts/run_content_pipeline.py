from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.editorial.pipeline import generate_editorial_files
from app.publish.exporter import default_output_dir
from app.schemas import PaperRecord
from app.summarization.schemas import PaperInsightRecord


@dataclass
class _DemoPaper:
    title: str
    venue: str


def _build_demo_inputs(limit: int) -> list[tuple[PaperRecord, PaperInsightRecord]]:
    pairs: list[tuple[PaperRecord, PaperInsightRecord]] = []
    for index in range(limit):
        paper = PaperRecord(
            source="demo",
            source_paper_id=f"demo-{index}",
            title=f"Demo Paper {index + 1}",
            abstract="A concise abstract for demo purposes.",
            full_text="This full text contains vision and video clues for template branching.",
            authors=["Author A"],
            paper_url=f"https://example.test/paper/{index}",
            venue="CVPR 2026",
        )
        insight = PaperInsightRecord(
            summary_short="提出了更稳定的训练与推理策略。",
            summary_long="该论文围绕视觉理解任务提出统一的训练框架。",
            novelty_points=["统一训练范式", "更强鲁棒性", "更低推理成本"],
            limitations=["需要更大规模数据进一步验证"],
            applications=["视觉检索", "视频理解", "内容生产辅助"],
            confidence_score=0.82,
        )
        pairs.append((paper, insight))
    return pairs


def main() -> int:
    limit = 3
    if len(sys.argv) > 2 and sys.argv[1] == "--limit":
        limit = int(sys.argv[2])

    output_dir = default_output_dir(Path(_ROOT))
    result = generate_editorial_files(papers_with_insights=_build_demo_inputs(limit), output_dir=output_dir)
    print(f"generated={result.generated}")
    for path in result.outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
