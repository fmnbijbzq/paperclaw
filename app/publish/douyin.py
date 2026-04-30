"""Douyin (TikTok China) publishing adapter (stub implementation)."""
from __future__ import annotations

from typing import Any

from app.publish.base import BasePublisher, PublishResult


class DouyinPublisher(BasePublisher):
    """Stub publisher for Douyin (抖音).

    In production this would use the Douyin content creation API.
    Currently returns a simulated result for testing the distribution pipeline.
    """

    @property
    def platform_name(self) -> str:
        return "douyin"

    def publish(
        self,
        *,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> PublishResult:
        # TODO: integrate with Douyin open API
        return PublishResult(
            success=False,
            platform=self.platform_name,
            external_id=None,
            external_url=None,
            error_message="stub: not yet integrated with Douyin API",
            metadata=metadata or {},
        )

    def check_status(self, external_id: str) -> PublishResult:
        return PublishResult(
            success=False,
            platform=self.platform_name,
            external_id=external_id,
            error_message="stub: status check not yet implemented",
        )
