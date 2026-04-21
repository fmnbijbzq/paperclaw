from __future__ import annotations

from dataclasses import dataclass, field
import logging

from app.storage import Database

LOGGER = logging.getLogger(__name__)


@dataclass
class NotificationCycleSummary:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    attempted_titles: list[str] = field(default_factory=list)
    succeeded_titles: list[str] = field(default_factory=list)
    failed_titles: list[str] = field(default_factory=list)


def run_notification_cycle(
    *,
    database_url: str,
    notifier,
    batch_size: int,
    destination: str,
) -> NotificationCycleSummary:
    db = Database(database_url)
    db.create_schema()
    summary = NotificationCycleSummary()
    selected_papers = db.list_unnotified_papers(destination=destination, limit=batch_size)
    send_limit = getattr(notifier, "max_items", None)
    papers = selected_papers if send_limit is None else selected_papers[:send_limit]

    LOGGER.info("本轮待发送论文数：%s，计划处理：%s", len(selected_papers), len(papers))
    if not papers:
        LOGGER.info("没有待发送论文，结束本轮发送")
        return summary

    return _send_combined_batch(db=db, notifier=notifier, destination=destination, papers=papers, summary=summary)


def _send_combined_batch(*, db: Database, notifier, destination: str, papers: list, summary: NotificationCycleSummary):
    titles = [paper.title for paper in papers]
    summary.attempted = len(papers)
    summary.attempted_titles.extend(titles)
    LOGGER.info("准备发送合并飞书消息：%s", titles)

    try:
        notifier.send_combined(papers)
    except Exception as exc:
        LOGGER.exception("飞书合并消息发送失败")
        db.record_notifications(destination=destination, papers=papers, success=False, error_message=str(exc))
        summary.failed = len(papers)
        summary.failed_titles.extend(titles)
        return summary

    db.record_notifications(destination=destination, papers=papers, success=True)
    summary.succeeded = len(papers)
    summary.succeeded_titles.extend(titles)
    LOGGER.info("飞书合并消息发送成功：%s", titles)
    return summary
