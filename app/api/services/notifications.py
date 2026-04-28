from __future__ import annotations

from datetime import timezone

from sqlalchemy import select

from app.api.schemas import NotificationFeedItem, NotificationItem, NotificationRetryResultItem
from app.models import Notification, Paper
from app.storage import Database


def _iso(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def list_notification_feed(db: Database) -> list[NotificationFeedItem]:
    with db._session() as session:
        rows = session.execute(
            select(Notification, Paper)
            .join(Paper, Paper.paper_id == Notification.paper_id)
            .order_by(Notification.notification_id.asc())
        ).all()

    return [
        NotificationFeedItem(
            notification=NotificationItem(
                notificationId=notification.notification_id,
                destination=notification.destination,
                paperId=notification.paper_id,
                success=notification.success,
                errorMessage=notification.error_message,
                sentAt=_iso(notification.sent_at),
            ),
            paperTitle=paper.title,
            source=paper.source,
        )
        for notification, paper in rows
    ]


def retry_notifications(
    db: Database,
    *,
    notifier,
    destination: str,
    notification_ids: list[int] | None = None,
    paper_ids: list[int] | None = None,
) -> list[NotificationRetryResultItem]:
    if notifier is None:
        raise ValueError("notification notifier is not configured")

    with db._session() as session:
        papers_by_id: dict[int, Paper] = {}
        if notification_ids:
            rows = session.execute(
                select(Notification, Paper)
                .join(Paper, Paper.paper_id == Notification.paper_id)
                .where(Notification.notification_id.in_(notification_ids), Notification.destination == destination)
                .order_by(Notification.notification_id.asc())
            ).all()
            for _, paper in rows:
                papers_by_id[paper.paper_id] = paper
        if paper_ids:
            for paper in session.scalars(select(Paper).where(Paper.paper_id.in_(paper_ids)).order_by(Paper.paper_id.asc())):
                papers_by_id[paper.paper_id] = paper

        papers = list(papers_by_id.values())

    results: list[NotificationRetryResultItem] = []
    for paper in papers:
        try:
            notifier.send_paper(paper)
        except Exception as exc:
            db.record_notification_attempt(destination=destination, paper=paper, success=False, error_message=str(exc))
            results.append(
                NotificationRetryResultItem(
                    paperId=paper.paper_id,
                    title=paper.title,
                    destination=destination,
                    success=False,
                    errorMessage=str(exc),
                )
            )
            continue

        db.record_notification_attempt(destination=destination, paper=paper, success=True)
        results.append(
            NotificationRetryResultItem(
                paperId=paper.paper_id,
                title=paper.title,
                destination=destination,
                success=True,
                errorMessage=None,
            )
        )

    return results
