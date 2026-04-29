"""Base publisher interface for distributing content to platforms."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PublishResult:
    """Result of a publish attempt to a platform."""
    success: bool
    platform: str
    external_id: str | None = None
    external_url: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    published_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class BasePublisher(ABC):
    """Abstract base class for platform publishers.

    Each platform (bilibili, xiaohongshu, douyin, etc.) should implement
    a concrete subclass with the actual publishing logic.

    Subclasses must implement:
    - `publish()`  — send content to the platform
    - `check_status()` — query the platform for a previous publish status
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the canonical platform identifier, e.g. 'bilibili'."""
        ...

    @abstractmethod
    def publish(
        self,
        *,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> PublishResult:
        """Publish content to the platform.

        Parameters
        ----------
        title : str
            Content title.
        content : str
            Full markdown or HTML content.
        metadata : dict, optional
            Platform-specific metadata (tags, category, cover URL, etc.).

        Returns
        -------
        PublishResult
            Outcome of the publish attempt.
        """
        ...

    @abstractmethod
    def check_status(self, external_id: str) -> PublishResult:
        """Check the status of a previously published item.

        Parameters
        ----------
        external_id : str
            The platform-specific ID returned by a prior `publish()` call.

        Returns
        -------
        PublishResult
            Current status of the item on the platform.
        """
        ...
