from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import create_envelope
from app.api.services.pipeline_summary import build_pipeline_summary

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/summary")
def get_pipeline_summary(request: Request) -> dict:
    payload = build_pipeline_summary(request.app.state.db, request.app.state.editorial_root)
    return create_envelope(payload).model_dump(by_alias=True)
