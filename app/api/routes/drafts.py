from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    EditorialDraftActionRequest,
    EditorialDraftAssignRequest,
    EditorialDraftExportRequest,
    EditorialDraftsResponse,
    ExportRecordsResponse,
    create_envelope,
)
from app.api.services.editorial_workflow import export_draft, get_draft_detail, list_drafts, list_exports

router = APIRouter(tags=["drafts"])


def _raise_draft_error(exc: ValueError) -> None:
    message = str(exc)
    status_code = 404 if "does not exist" in message else 409
    raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/drafts")
def get_drafts(request: Request) -> dict:
    items = list_drafts(request.app.state.db)
    return create_envelope(EditorialDraftsResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/drafts/{draft_id}")
def get_draft(request: Request, draft_id: str) -> dict:
    payload = get_draft_detail(request.app.state.db, draft_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/drafts/{draft_id}/assign")
def assign_draft(request: Request, draft_id: str, body: EditorialDraftAssignRequest) -> dict:
    try:
        draft = request.app.state.db.assign_editorial_draft(draft_id, assignee=body.assignee, actor=body.actor)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = get_draft_detail(request.app.state.db, draft.draft_id)
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/drafts/{draft_id}/review")
def review_draft(request: Request, draft_id: str, body: EditorialDraftActionRequest) -> dict:
    try:
        draft = request.app.state.db.review_editorial_draft(draft_id, actor=body.actor, note=body.note)
    except ValueError as exc:
        _raise_draft_error(exc)
    payload = get_draft_detail(request.app.state.db, draft.draft_id)
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/drafts/{draft_id}/approve")
def approve_draft(request: Request, draft_id: str, body: EditorialDraftActionRequest) -> dict:
    try:
        draft = request.app.state.db.approve_editorial_draft(draft_id, actor=body.actor, note=body.note)
    except ValueError as exc:
        _raise_draft_error(exc)
    payload = get_draft_detail(request.app.state.db, draft.draft_id)
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/drafts/{draft_id}/reject")
def reject_draft(request: Request, draft_id: str, body: EditorialDraftActionRequest) -> dict:
    try:
        draft = request.app.state.db.reject_editorial_draft(draft_id, actor=body.actor, note=body.note)
    except ValueError as exc:
        _raise_draft_error(exc)
    payload = get_draft_detail(request.app.state.db, draft.draft_id)
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/drafts/{draft_id}/export")
def export_draft_route(request: Request, draft_id: str, body: EditorialDraftExportRequest) -> dict:
    try:
        payload = export_draft(request.app.state.db, draft_id=draft_id, exported_by=body.exported_by)
    except ValueError as exc:
        _raise_draft_error(exc)
    return create_envelope(payload).model_dump(by_alias=True)


@router.get("/exports")
def get_exports(request: Request) -> dict:
    items = list_exports(request.app.state.db)
    return create_envelope(ExportRecordsResponse(items=items, total=len(items))).model_dump(by_alias=True)
