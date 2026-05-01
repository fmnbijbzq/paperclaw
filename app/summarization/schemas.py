from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperInsightRecord:
    summary_short: str
    summary_long: str
    novelty_points: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    confidence_score: float | None = None
    is_placeholder: bool = True
    generator: str = "template-v1"
