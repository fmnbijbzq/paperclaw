from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.summarization.schemas import PaperInsightRecord


@dataclass
class EditorialDraft:
    platform: str
    title: str
    hook: str
    body: str
    tags: list[str]


class EditorialComposer:
    def __init__(self, templates_dir: str) -> None:
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def compose(self, *, platform: str, paper: Any, insight: PaperInsightRecord) -> EditorialDraft:
        platform_key = platform.lower()
        template_name = {
            "bilibili": "bilibili.md.j2",
            "xiaohongshu": "xiaohongshu.md.j2",
            "douyin": "douyin.md.j2",
        }.get(platform_key)
        if template_name is None:
            raise ValueError(f"Unsupported platform: {platform}")

        title = self._build_title(platform_key, paper)
        hook = self._build_hook(platform_key, insight)
        tags = self._build_tags(platform_key, paper)

        template = self.env.get_template(template_name)
        body = template.render(
            paper=paper,
            insight=insight,
            title=title,
            hook=hook,
            tags=tags,
        )

        return EditorialDraft(
            platform=platform_key,
            title=title,
            hook=hook,
            body=body.strip(),
            tags=tags,
        )

    @staticmethod
    def _build_title(platform: str, paper: Any) -> str:
        base = getattr(paper, "title", "未命名论文")
        if platform == "bilibili":
            return f"一文看懂：{base}"
        if platform == "xiaohongshu":
            return f"AI论文速递｜{base}"
        return f"60秒讲论文：{base}"

    @staticmethod
    def _build_hook(platform: str, insight: PaperInsightRecord) -> str:
        snippet = insight.summary_short[:60]
        if platform == "bilibili":
            return f"这篇论文为什么值得看？因为它把核心问题讲透了：{snippet}"
        if platform == "xiaohongshu":
            return f"今天这篇真的有料：{snippet}"
        return f"先说结论：{snippet}"

    @staticmethod
    def _build_tags(platform: str, paper: Any) -> list[str]:
        base_tags = ["AI", "论文解读", "科研"]
        venue = getattr(paper, "venue", None)
        if venue:
            base_tags.append(str(venue).replace(" ", ""))
        if platform == "xiaohongshu":
            base_tags.extend(["学习打卡", "技术成长"])
        if platform == "douyin":
            base_tags.extend(["干货", "一分钟知识"])
        return base_tags[:8]
