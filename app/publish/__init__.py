"""Publisher adapter registry."""
from __future__ import annotations

from app.publish.base import BasePublisher, PublishResult
from app.publish.bilibili import BilibiliPublisher
from app.publish.douyin import DouyinPublisher
from app.publish.exporter import default_output_dir, export_reviewed_markdown
from app.publish.xiaohongshu import XiaohongshuPublisher

# Registry of available publisher adapters keyed by platform name
_PUBLISHERS: dict[str, type[BasePublisher]] = {
    "bilibili": BilibiliPublisher,
    "xiaohongshu": XiaohongshuPublisher,
    "douyin": DouyinPublisher,
}


def get_publisher(platform: str) -> BasePublisher:
    """Return a publisher instance for the given platform.

    Raises ValueError if the platform is not registered.
    """
    cls = _PUBLISHERS.get(platform)
    if cls is None:
        available = ", ".join(sorted(_PUBLISHERS))
        raise ValueError(f"unknown platform '{platform}'; available: {available}")
    return cls()


def list_platforms() -> list[str]:
    """Return the list of registered platform names."""
    return sorted(_PUBLISHERS)


__all__ = [
    "BasePublisher",
    "PublishResult",
    "BilibiliPublisher",
    "DouyinPublisher",
    "XiaohongshuPublisher",
    "default_output_dir",
    "export_reviewed_markdown",
    "get_publisher",
    "list_platforms",
]
