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
    send_mode: str,
    destination: str,
) -> NotificationCycleSummary:
    db = Database(database_url)
    db.create_schema()
    summary = NotificationCycleSummary()
    papers = db.list_unnotified_papers(destination=destination, limit=batch_size)

    LOGGER.info("本轮待发送论文数：%s，计划处理：%s", len(papers), min(len(papers), batch_size))
    if not papers:
        LOGGER.info("没有待发送论文，结束本轮发送")
        return summary

    if send_mode == "combined":
        return _send_combined_batch(db=db, notifier=notifier, destination=destination, papers=papers, summary=summary)
    if send_mode == "per_paper":
        return _send_per_paper(db=db, notifier=notifier, destination=destination, papers=papers, summary=summary)

    raise ValueError(f"unsupported notify send mode: {send_mode}")


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


def _send_per_paper(*, db: Database, notifier, destination: str, papers: list, summary: NotificationCycleSummary):
    for paper in papers:
        title = paper.title
        summary.attempted += 1
        summary.attempted_titles.append(title)
        LOGGER.info("准备发送单篇飞书消息：%s", title)
        try:
            notifier.send_paper(paper)
        except Exception as exc:
            LOGGER.exception("飞书单篇消息发送失败：%s", title)
            db.record_notification_attempt(
                destination=destination,
                paper=paper,
                success=False,
                error_message=str(exc),
            )
            summary.failed += 1
            summary.failed_titles.append(title)
            continue

        db.record_notification_attempt(destination=destination, paper=paper, success=True)
        summary.succeeded += 1
        summary.succeeded_titles.append(title)
        LOGGER.info("飞书单篇消息发送成功：%s", title)

    return summary
