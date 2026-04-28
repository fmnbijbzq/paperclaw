from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import NotificationFeedResponse, NotificationRetryRequest, NotificationRetryResponse, create_envelope
from app.api.services.notifications import list_notification_feed, retry_notifications

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def get_notifications(request: Request) -> dict:
    items = list_notification_feed(request.app.state.db)
    failed_count = sum(1 for item in items if not item.notification.success)
    successful_count = sum(1 for item in items if item.notification.success)
    payload = NotificationFeedResponse(
        items=items,
        total=len(items),
        failedCount=failed_count,
        successfulCount=successful_count,
    )
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/notifications/retry")
def retry_notification_route(request: Request, body: NotificationRetryRequest) -> dict:
    if not body.notification_ids and not body.paper_ids:
        raise HTTPException(status_code=400, detail="notificationIds or paperIds is required")
    try:
        items = retry_notifications(
            request.app.state.db,
            notifier=getattr(request.app.state, "notification_notifier", None),
            destination=body.destination,
            notification_ids=body.notification_ids,
            paper_ids=body.paper_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = NotificationRetryResponse(
        items=items,
        requested=len(body.notification_ids or []) + len(body.paper_ids or []),
        attempted=len(items),
        succeeded=sum(1 for item in items if item.success),
        failed=sum(1 for item in items if not item.success),
    )
    return create_envelope(payload).model_dump(by_alias=True)
