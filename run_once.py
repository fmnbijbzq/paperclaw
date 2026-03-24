from __future__ import annotations

from pathlib import Path
import logging

from app.config import AppSettings, load_source_config
from app.logging import configure_logging
from app.notifiers.feishu_bot import FeishuBotNotifier
from app.pipeline import run_pipeline
from app.sources.arxiv import ArxivSource
from app.sources.openreview import OpenReviewSource

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"


def run_pipeline_from_config() -> int:
    settings = AppSettings()
    configure_logging(settings)
    source_config = load_source_config(SOURCE_CONFIG_PATH)

    sources = []
    arxiv_config = source_config.get("arxiv", {})
    if arxiv_config.get("enabled"):
        sources.append(
            ArxivSource(
                allowed_categories=arxiv_config.get("categories"),
                lookback_days=arxiv_config.get("lookback_days"),
            )
        )

    openreview_config = source_config.get("openreview", {})
    if openreview_config.get("enabled"):
        sources.append(
            OpenReviewSource(
                venues=openreview_config.get("venues"),
                lookback_days=openreview_config.get("lookback_days"),
            )
        )

    notifier = None
    if settings.feishu_bot_webhook:
        notifier = FeishuBotNotifier(
            settings.feishu_bot_webhook,
            max_items=settings.max_notify_items,
        )

    run_pipeline(
        database_url=settings.database_url,
        sources=sources,
        notifier=notifier,
    )
    return 0


def main() -> int:
    try:
        return run_pipeline_from_config()
    except Exception:
        LOGGER.exception("paperclaw run failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
