from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Request

from app.api.schemas import (
    CrawlRunItem,
    CrawlRunsResponse,
    EditorialRunItem,
    EditorialRunsResponse,
    SummarizationRunItem,
    SummarizationRunsResponse,
    create_envelope,
)
from app.api.services.pipeline_summary import build_pipeline_summary

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _duration_seconds(started_at, finished_at) -> float | None:
    if started_at is None or finished_at is None:
        return None
    delta = finished_at - started_at
    return round(delta.total_seconds(), 2)


@router.get("/summary")
def get_pipeline_summary(request: Request) -> dict:
    payload = build_pipeline_summary(request.app.state.db, request.app.state.editorial_root)
    return create_envelope(payload).model_dump(by_alias=True)


@router.get("/runs/crawl")
def list_crawl_runs(request: Request, source: str | None = None, limit: int = 50) -> dict:
    db = request.app.state.db
    runs = db.list_crawl_runs(source=source, limit=limit)
    items = [
        CrawlRunItem(
            runId=run.run_id,
            source=run.source,
            status=run.status,
            fetchedCount=run.fetched_count,
            newCount=run.new_count,
            errorMessage=run.error_message,
            startedAt=_iso(run.started_at),
            finishedAt=_iso(run.finished_at),
            durationSeconds=_duration_seconds(run.started_at, run.finished_at),
        )
        for run in runs
    ]
    return create_envelope(CrawlRunsResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/runs/summarization")
def list_summarization_runs(request: Request, limit: int = 50) -> dict:
    db = request.app.state.db
    runs = db.list_summarization_runs(limit=limit)
    items = [
        SummarizationRunItem(
            runId=run.run_id,
            status=run.status,
            papersProcessed=run.papers_processed,
            insightsGenerated=run.insights_generated,
            errorMessage=run.error_message,
            startedAt=_iso(run.started_at),
            finishedAt=_iso(run.finished_at),
            durationSeconds=_duration_seconds(run.started_at, run.finished_at),
        )
        for run in runs
    ]
    return create_envelope(SummarizationRunsResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/runs/editorial")
def list_editorial_runs(request: Request, limit: int = 50) -> dict:
    db = request.app.state.db
    runs = db.list_editorial_runs(limit=limit)
    items = [
        EditorialRunItem(
            runId=run.run_id,
            status=run.status,
            papersProcessed=run.papers_processed,
            draftsGenerated=run.drafts_generated,
            errorMessage=run.error_message,
            startedAt=_iso(run.started_at),
            finishedAt=_iso(run.finished_at),
            durationSeconds=_duration_seconds(run.started_at, run.finished_at),
        )
        for run in runs
    ]
    return create_envelope(EditorialRunsResponse(items=items, total=len(items))).model_dump(by_alias=True)
