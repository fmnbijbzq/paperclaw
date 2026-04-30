from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    CrawlRunItem,
    CrawlRunsResponse,
    EditorialRunItem,
    EditorialRunsResponse,
    PipelineTaskCreateRequest,
    PipelineTaskItem,
    PipelineTasksResponse,
    SummarizationRunItem,
    SummarizationRunsResponse,
    create_envelope,
)
from app.api.services.pipeline_summary import build_pipeline_summary
from app.models import PipelineTask

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


def _task_to_item(task: PipelineTask) -> PipelineTaskItem:
    return PipelineTaskItem(
        taskId=task.task_id,
        taskType=task.task_type,
        status=task.status,
        currentStage=task.current_stage,
        progressCurrent=task.progress_current,
        progressTotal=task.progress_total,
        requestedBy=task.requested_by,
        parameters=dict(task.parameters or {}),
        result=dict(task.result or {}),
        errorMessage=task.error_message,
        createdAt=_iso(task.created_at),
        startedAt=_iso(task.started_at) or None,
        finishedAt=_iso(task.finished_at) or None,
    )


@router.get("/summary")
async def get_pipeline_summary(request: Request) -> dict:
    payload = build_pipeline_summary(request.app.state.db, request.app.state.editorial_root)
    return create_envelope(payload).model_dump(by_alias=True)


@router.post("/tasks")
async def create_pipeline_task(request: Request, body: PipelineTaskCreateRequest) -> dict:
    if body.task_type != "full_pipeline":
        raise HTTPException(status_code=400, detail="unsupported pipeline task type")
    parameters = {
        "notify": body.notify,
        "editorialLimit": body.editorial_limit,
    }
    task = request.app.state.db.create_pipeline_task(
        task_type=body.task_type,
        requested_by=body.requested_by,
        parameters=parameters,
    )
    runner = getattr(request.app.state, "pipeline_task_runner", None)
    if runner is not None:
        runner.enqueue(task.task_id)
    return create_envelope(_task_to_item(task)).model_dump(by_alias=True)


@router.get("/tasks")
async def list_pipeline_tasks(request: Request, limit: int = 50) -> dict:
    tasks = request.app.state.db.list_pipeline_tasks(limit=limit)
    items = [_task_to_item(task) for task in tasks]
    return create_envelope(PipelineTasksResponse(items=items, total=len(items))).model_dump(by_alias=True)


@router.get("/tasks/{task_id}")
async def get_pipeline_task(request: Request, task_id: int) -> dict:
    task = request.app.state.db.get_pipeline_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="pipeline task not found")
    return create_envelope(_task_to_item(task)).model_dump(by_alias=True)


@router.post("/tasks/{task_id}/cancel")
async def cancel_pipeline_task(request: Request, task_id: int) -> dict:
    try:
        task = request.app.state.db.cancel_pipeline_task(task_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 409
        raise HTTPException(status_code=status_code, detail=message) from exc
    return create_envelope(_task_to_item(task)).model_dump(by_alias=True)


@router.get("/runs/crawl")
async def list_crawl_runs(request: Request, source: str | None = None, limit: int = 50) -> dict:
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
async def list_summarization_runs(request: Request, limit: int = 50) -> dict:
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
async def list_editorial_runs(request: Request, limit: int = 50) -> dict:
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
