from __future__ import annotations

import logging

from app.config import AppSettings
from app.logging import configure_logging
from app.notification_pipeline import run_notification_cycle
from app.notifiers.feishu_bot import FeishuBotNotifier

LOGGER = logging.getLogger(__name__)


def run_notify_once_from_config() -> int:
    settings = AppSettings()
    configure_logging(settings)

    if not settings.feishu_bot_webhook:
        LOGGER.warning("未配置 FEISHU_BOT_WEBHOOK，跳过飞书发送")
        return 0

    notifier = FeishuBotNotifier(
        settings.feishu_bot_webhook,
        secret=settings.feishu_bot_secret,
        max_items=settings.notify_batch_size,
    )
    summary = run_notification_cycle(
        database_url=settings.database_url,
        notifier=notifier,
        batch_size=settings.notify_batch_size,
        send_mode=settings.notify_send_mode,
        destination="feishu",
    )
    LOGGER.info(
        "飞书发送完成：尝试 %s 篇，成功 %s 篇，失败 %s 篇",
        summary.attempted,
        summary.succeeded,
        summary.failed,
    )
    return 0


def main() -> int:
    try:
        return run_notify_once_from_config()
    except Exception:
        LOGGER.exception("paperclaw notification run failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
