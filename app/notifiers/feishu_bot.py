from __future__ import annotations

from collections.abc import Sequence

import httpx


class FeishuBotNotifier:
    def __init__(
        self,
        webhook_url: str,
        *,
        max_items: int = 10,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.max_items = max_items
        self.timeout = timeout
        self._transport = transport

    def build_payload(
        self,
        *,
        summary_title: str,
        papers: Sequence[dict],
        stats: dict | None = None,
    ) -> dict:
        visible_papers = list(papers)[: self.max_items]
        lines = [summary_title]

        if stats:
            stat_line = ", ".join(f"{key}={value}" for key, value in stats.items())
            if stat_line:
                lines.append(stat_line)

        for paper in visible_papers:
            title = paper.get("title", "Untitled")
            paper_url = paper.get("paper_url", "")
            lines.append(f"- {title}")
            if paper_url:
                lines.append(str(paper_url))

        return {
            "msg_type": "text",
            "content": {
                "text": "\n".join(lines),
            },
        }

    def send(self, payload: dict) -> dict:
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            response = client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
