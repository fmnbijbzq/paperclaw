from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    DestinationCreateRequest,
    DestinationCreateResponse,
    DestinationRecordItem,
    DestinationRecordsResponse,
    DestinationUpdateRequest,
    create_envelope,
)
from app.models import DestinationRecord
from app.storage import Database

router = APIRouter(tags=["destinations"])


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _destination_to_item(record: DestinationRecord) -> DestinationRecordItem:
    return DestinationRecordItem(
        destinationId=record.destination_id,
        draftId=record.draft_id,
        platform=record.platform,
        status=record.status,
        publishResult=record.publish_result,
        callbackUrl=record.callback_url,
        createdAt=_iso(record.created_at),
        updatedAt=_iso(record.updated_at),
    )


@router.get("/destinations")
def list_destinations(
    request: Request,
    draft_id: str | None = None,
    platform: str | None = None,
) -> dict:
    db: Database = request.app.state.db
    records = db.list_destination_records(draft_id=draft_id, platform=platform)
    items = [_destination_to_item(r) for r in records]
    return create_envelope(
        DestinationRecordsResponse(items=items, total=len(items))
    ).model_dump(by_alias=True)


@router.get("/destinations/{draft_id}")
def get_destinations_for_draft(request: Request, draft_id: str) -> dict:
    db: Database = request.app.state.db
    records = db.list_destination_records(draft_id=draft_id)
    items = [_destination_to_item(r) for r in records]
    return create_envelope(
        DestinationRecordsResponse(items=items, total=len(items))
    ).model_dump(by_alias=True)


@router.post("/destinations")
def create_destination(request: Request, body: DestinationCreateRequest) -> dict:
    db: Database = request.app.state.db
    try:
        record = db.create_destination_record(
            draft_id=body.draft_id,
            platform=body.platform,
            status=body.status,
            publish_result=body.publish_result,
            callback_url=body.callback_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return create_envelope(
        _destination_to_item(record)
    ).model_dump(by_alias=True)


@router.patch("/destinations/{destination_id}")
def update_destination(request: Request, destination_id: int, body: DestinationUpdateRequest) -> dict:
    db: Database = request.app.state.db
    try:
        record = db.update_destination_record(
            destination_id,
            status=body.status,
            publish_result=body.publish_result,
            callback_url=body.callback_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return create_envelope(
        _destination_to_item(record)
    ).model_dump(by_alias=True)
