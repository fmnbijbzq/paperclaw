"""Xiaohongshu (Little Red Book) publishing adapter (stub implementation)."""
from __future__ import annotations

from typing import Any

from app.publish.base import BasePublisher, PublishResult
from app.utils.time import utc_now


class XiaohongshuPublisher(BasePublisher):
    """Stub publisher for Xiaohongshu (小红书).

    In production this would use the Xiaohongshu creator API or web automation.
    Currently returns a simulated result for testing the distribution pipeline.
    """

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    def publish(
        self,
        *,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> PublishResult:
        # TODO: integrate with Xiaohongshu API / automation
        return PublishResult(
            success=True,
            platform=self.platform_name,
            external_id=None,
            external_url=None,
            error_message="stub: not yet integrated with Xiaohongshu API",
            metadata=metadata or {},
            published_at=utc_now(),
        )

    def check_status(self, external_id: str) -> PublishResult:
        return PublishResult(
            success=False,
            platform=self.platform_name,
            external_id=external_id,
            error_message="stub: status check not yet implemented",
        )
