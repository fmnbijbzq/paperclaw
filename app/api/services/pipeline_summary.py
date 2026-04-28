from __future__ import annotations

from datetime import timezone
from pathlib import Path

from sqlalchemy import func, select

from app.api.schemas import PipelineStageItem, PipelineSummaryMetrics, PipelineSummaryResponse, SourceHealthItem
from app.models import CrawlRun, EditorialDraft, Notification, Paper, PaperInsight
from app.storage import Database


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _build_stage_definitions() -> list[PipelineStageItem]:
    return [
        PipelineStageItem(
            stageId="fetch",
            name="Fetch",
            status="live",
            summary="Source crawlers pull from arXiv, OpenReview, and CVF using source-specific adapters.",
            implementedIn=["app/sources/arxiv.py", "app/sources/openreview.py", "app/sources/cvf.py"],
            evidence="Crawl adapters already exist and run through the Python ingestion pipeline.",
        ),
        PipelineStageItem(
            stageId="normalize",
            name="Normalize",
            status="live",
            summary="Raw payloads are normalized into a shared paper model before storage and downstream enrichment.",
            implementedIn=["app/normalizer.py", "app/models.py"],
            evidence="Normalized metadata is persisted to the shared SQLAlchemy models.",
        ),
        PipelineStageItem(
            stageId="store",
            name="Store",
            status="live",
            summary="Papers, versions, insights, and notifications are stored in SQLite-backed SQLAlchemy tables.",
            implementedIn=["app/storage.py", "app/models.py"],
            evidence="Persistent entities back the existing CLI workflows.",
        ),
        PipelineStageItem(
            stageId="insight",
            name="Insight",
            status="live",
            summary="Summaries, novelty points, limitations, and applications are generated and attached to papers.",
            implementedIn=["app/summarization/service.py", "app/models.py"],
            evidence="PaperInsight already captures the frontend detail-page content shape.",
        ),
        PipelineStageItem(
            stageId="editorial",
            name="Editorial",
            status="live",
            summary="Platform-specific markdown drafts are composed for Bilibili, Xiaohongshu, and Douyin.",
            implementedIn=["app/editorial/pipeline.py", "app/editorial/composer.py"],
            evidence="Draft generation writes per-platform markdown files to the outputs directory.",
        ),
        PipelineStageItem(
            stageId="export",
            name="Export",
            status="partial",
            summary="Reviewed markdown can be exported, but approval workflow and richer destination tracking are future extension points.",
            implementedIn=["app/publish/exporter.py", "scripts/export_for_publish.py"],
            evidence="Current export copies reviewed markdown without frontend-level approvals or audit UI.",
        ),
    ]


def _map_status(run: CrawlRun) -> str:
    if run.status == "success":
        return "healthy"
    if run.status == "failed":
        return "degraded"
    return "attention"


def build_pipeline_summary(db: Database, editorial_root: Path) -> PipelineSummaryResponse:
    del editorial_root
    with db._session() as session:
        total_papers = session.scalar(select(func.count()).select_from(Paper)) or 0
        papers_with_insights = session.scalar(select(func.count()).select_from(PaperInsight)) or 0

        successful_notified_ids = set(
            session.scalars(select(Notification.paper_id).where(Notification.success.is_(True))).all()
        )
        pending_notifications = total_papers - len(successful_notified_ids)

        crawl_runs = list(session.scalars(select(CrawlRun).order_by(CrawlRun.run_id.asc())).all())
        db_draft_count = session.scalar(select(func.count()).select_from(EditorialDraft)) or 0

    latest_by_source: dict[str, CrawlRun] = {}
    for run in crawl_runs:
        latest_by_source[run.source] = run

    source_health = [
        SourceHealthItem(
            source=source,
            enabled=True,
            status=_map_status(run),
            lastRunAt=_iso(run.finished_at or run.started_at),
            fetchedCount=run.fetched_count,
            newCount=run.new_count,
            notes=run.error_message or f"Latest crawl run finished with status: {run.status}.",
        )
        for source, run in sorted(latest_by_source.items())
    ]

    return PipelineSummaryResponse(
        metrics=PipelineSummaryMetrics(
            totalPapers=total_papers,
            papersWithInsights=papers_with_insights,
            pendingNotifications=pending_notifications,
            editorialDrafts=db_draft_count,
        ),
        stages=_build_stage_definitions(),
        sourceHealth=source_health,
    )
