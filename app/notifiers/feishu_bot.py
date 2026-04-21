from __future__ import annotations

from collections.abc import Sequence
import base64
import hashlib
import hmac
import logging
import time

import httpx

LOGGER = logging.getLogger(__name__)


class FeishuBotNotifier:
    def __init__(
        self,
        webhook_url: str,
        *,
        secret: str | None = None,
        max_items: int = 10,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.secret = secret
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
        request_payload = self._build_request_payload(payload)
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            response = client.post(self.webhook_url, json=request_payload)
            response.raise_for_status()
            result = response.json()
            status_code = result.get("StatusCode", 0)
            if status_code != 0:
                status_message = result.get("StatusMessage", "unknown error")
                raise RuntimeError(f"Feishu webhook failed with StatusCode={status_code}: {status_message}")
            return result

    def send_combined(self, papers: Sequence[object]) -> dict:
        payload = self.build_payload(
            summary_title="AI Vision Papers Daily Digest",
            papers=[self._coerce_paper(paper) for paper in papers],
            stats={"count": len(papers)},
        )
        LOGGER.info("发送飞书合并消息，包含 %s 篇论文", len(papers))
        return self.send(payload)

    def send_paper(self, paper: object) -> dict:
        paper_data = self._coerce_paper(paper)
        payload = self.build_payload(
            summary_title="AI Vision Papers Daily Digest",
            papers=[paper_data],
        )
        LOGGER.info("发送飞书单篇消息：%s", paper_data["title"])
        return self.send(payload)

    def notify(self, summary) -> dict:
        return self.send_combined(summary.new_papers[: self.max_items])

    def _build_request_payload(self, payload: dict) -> dict:
        if not self.secret:
            return payload

        timestamp = str(int(time.time()))
        request_payload = dict(payload)
        request_payload["timestamp"] = timestamp
        request_payload["sign"] = self._gen_sign(timestamp, self.secret)
        return request_payload

    @staticmethod
    def _gen_sign(timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    @staticmethod
    def _coerce_paper(paper: object) -> dict:
        if isinstance(paper, dict):
            return {
                "title": paper.get("title", "Untitled"),
                "paper_url": paper.get("paper_url", ""),
            }

        return {
            "title": getattr(paper, "title", "Untitled"),
            "paper_url": getattr(paper, "paper_url", ""),
        }
