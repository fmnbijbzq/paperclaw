from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import EditorialDraftsResponse, PaperDetailResponse, PaperInsightsResponse, PapersListResponse, create_envelope
from app.api.services.editorial_workflow import list_drafts
from app.api.services.read_models import get_paper_detail, list_paper_insights, list_papers

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("")
def get_papers(
    request: Request,
    q: str = "",
    source: str | None = None,
    category: str | None = None,
    venue: str | None = None,
    hasInsight: bool | None = None,
    hasDraft: bool | None = None,
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    db = request.app.state.db
    editorial_root = request.app.state.editorial_root
    items, total = list_papers(
        db,
        editorial_root,
        q=q,
        source=source,
        category=category,
        venue=venue,
        has_insight=hasInsight,
        has_draft=hasDraft,
        limit=limit,
        offset=offset,
    )
    return create_envelope(PapersListResponse(items=items, total=total, appliedQuery=q)).model_dump(by_alias=True)


@router.get("/insights")
def get_paper_insights(request: Request) -> dict:
    db = request.app.state.db
    items = list_paper_insights(db)
    return create_envelope(PaperInsightsResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/editorial-drafts")
def get_editorial_drafts(request: Request) -> dict:
    items = list_drafts(request.app.state.db)
    return create_envelope(EditorialDraftsResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/{paper_id}")
def get_paper(request: Request, paper_id: int) -> dict:
    db = request.app.state.db
    payload = get_paper_detail(db, paper_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="paper not found")
    return create_envelope(PaperDetailResponse(**payload.model_dump(by_alias=True))).model_dump(by_alias=True)
