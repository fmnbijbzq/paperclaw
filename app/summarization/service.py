from __future__ import annotations

from app.schemas import PaperRecord
from app.summarization.schemas import PaperInsightRecord


class SummarizationService:
    """Deterministic summary generator with graceful fallback.

    This service intentionally avoids external model calls so tests remain stable.
    The interface is designed to be replaceable with an LLM-backed implementation.
    """

    def generate(self, paper: PaperRecord) -> PaperInsightRecord:
        core_text = self._build_core_text(paper)
        summary_short = self._build_summary_short(paper)
        summary_long = self._build_summary_long(paper, core_text)
        novelty_points = self._build_novelty_points(paper, core_text)
        limitations = self._build_limitations(paper)
        applications = self._build_applications(paper, core_text)
        confidence = self._estimate_confidence(paper)

        return PaperInsightRecord(
            summary_short=summary_short,
            summary_long=summary_long,
            novelty_points=novelty_points,
            limitations=limitations,
            applications=applications,
            confidence_score=confidence,
        )

    @staticmethod
    def _build_core_text(paper: PaperRecord) -> str:
        for value in (paper.full_text, paper.abstract, paper.title):
            if value and value.strip():
                return " ".join(value.strip().split())
        return ""

    @staticmethod
    def _build_summary_short(paper: PaperRecord) -> str:
        if paper.abstract and paper.abstract.strip():
            normalized = " ".join(paper.abstract.strip().split())
            return normalized[:160]
        return f"{paper.title} 的核心思路需要结合原文进一步确认。"

    @staticmethod
    def _build_summary_long(paper: PaperRecord, core_text: str) -> str:
        if not core_text:
            return f"论文《{paper.title}》当前缺少正文和摘要，建议人工补充后再次生成总结。"
        return f"论文《{paper.title}》聚焦于 {core_text[:320]}"

    @staticmethod
    def _build_novelty_points(paper: PaperRecord, core_text: str) -> list[str]:
        points: list[str] = []
        if paper.title:
            points.append(f"提出或验证了与“{paper.title}”相关的技术路线。")
        if paper.venue:
            points.append(f"在 {paper.venue} 语境下给出了可复现的研究结果。")
        if core_text:
            points.append(f"核心贡献强调：{core_text[:120]}")
        while len(points) < 3:
            points.append("需要结合实验章节进一步提炼差异化贡献。")
        return points[:5]

    @staticmethod
    def _build_limitations(paper: PaperRecord) -> list[str]:
        limitations = ["当前自动摘要可能忽略实验细节，需人工复核关键指标。"]
        if not paper.full_text:
            limitations.append("未获得完整正文，结论主要基于摘要与标题。")
        return limitations

    @staticmethod
    def _build_applications(paper: PaperRecord, core_text: str) -> list[str]:
        apps = ["可用于技术调研周报与论文速览内容生产。"]
        if "video" in core_text.lower() or "vision" in core_text.lower() or "image" in core_text.lower():
            apps.append("可扩展到视觉任务基线选型与实验设计参考。")
        apps.append("可作为短视频/图文平台的研究解读素材。")
        return apps[:5]

    @staticmethod
    def _estimate_confidence(paper: PaperRecord) -> float:
        if paper.full_text and paper.abstract:
            return 0.86
        if paper.abstract:
            return 0.72
        return 0.55
