from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.utils.time import utc_now

API_SCHEMA_VERSION = "2026-04-27"

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ApiMeta(ApiModel):
    data_source: str = Field(default="http", alias="dataSource")
    generated_at: datetime = Field(alias="generatedAt")
    schema_version: str = Field(default=API_SCHEMA_VERSION, alias="schemaVersion")


class ApiEnvelope(ApiModel, Generic[T]):
    data: T
    meta: ApiMeta


class HealthResponse(ApiModel):
    status: str


class PaperItem(ApiModel):
    paper_id: int = Field(alias="paperId")
    source_paper_id: str = Field(alias="sourcePaperId")
    title: str
    abstract: str = ""
    authors: list[str]
    source: str
    venue: str = ""
    categories: list[str]
    paper_url: str = Field(alias="paperUrl")
    pdf_url: str = Field(default="", alias="pdfUrl")
    published_at: str = Field(default="", alias="publishedAt")
    updated_at_source: str = Field(default="", alias="updatedAtSource")


class PaperInsightItem(ApiModel):
    insight_id: int = Field(alias="insightId")
    paper_id: int = Field(alias="paperId")
    summary_short: str = Field(alias="summaryShort")
    summary_long: str = Field(alias="summaryLong")
    novelty_points: list[str] = Field(alias="noveltyPoints")
    limitations: list[str]
    applications: list[str]
    confidence_score: float | None = Field(alias="confidenceScore")
    updated_at: str = Field(alias="updatedAt")


class PaperInsightPreview(ApiModel):
    insight_id: int = Field(alias="insightId")
    summary_short: str = Field(alias="summaryShort")
    confidence_score: float | None = Field(alias="confidenceScore")
    updated_at: str = Field(alias="updatedAt")


class NotificationItem(ApiModel):
    notification_id: int = Field(alias="notificationId")
    destination: str
    paper_id: int = Field(alias="paperId")
    success: bool
    error_message: str | None = Field(alias="errorMessage")
    sent_at: str = Field(alias="sentAt")


class NotificationSummaryItem(ApiModel):
    total_attempts: int = Field(alias="totalAttempts")
    latest_status: str = Field(alias="latestStatus")
    last_sent_at: str | None = Field(alias="lastSentAt")


class PaperListItem(ApiModel):
    paper: PaperItem
    insight: PaperInsightPreview | None
    notification_summary: NotificationSummaryItem = Field(alias="notificationSummary")
    editorial_draft_count: int = Field(alias="editorialDraftCount")


class EditorialDraftSummaryItem(ApiModel):
    draft_id: str = Field(alias="draftId")
    paper_id: int = Field(alias="paperId")
    platform: str
    title: str
    hook: str
    status: str
    assignee: str | None = None
    updated_at: str = Field(alias="updatedAt")
    output_path: str = Field(alias="outputPath")


class PaperDetailItem(ApiModel):
    paper: PaperItem
    insight: PaperInsightItem | None
    notifications: list[NotificationItem]
    drafts: list[EditorialDraftSummaryItem]


class PapersListResponse(ApiModel):
    items: list[PaperListItem]
    total: int
    applied_query: str = Field(alias="appliedQuery")


class PaperDetailResponse(PaperDetailItem):
    pass


class EditorialDraftItem(ApiModel):
    draft_id: str = Field(alias="draftId")
    paper_id: int = Field(alias="paperId")
    platform: str
    title: str
    hook: str
    status: str
    assignee: str | None = None
    updated_at: str = Field(alias="updatedAt")
    output_path: str = Field(alias="outputPath")


class EditorialDraftDetailResponse(EditorialDraftItem):
    markdown_content: str = Field(alias="markdownContent")
    review_note: str | None = Field(default=None, alias="reviewNote")
    paper: PaperItem


class EditorialDraftActionRequest(ApiModel):
    actor: str
    note: str | None = None


class EditorialDraftAssignRequest(ApiModel):
    assignee: str
    actor: str | None = None


class EditorialDraftExportRequest(ApiModel):
    exported_by: str = Field(alias="exportedBy")


class ExportRecordItem(ApiModel):
    export_id: int = Field(alias="exportId")
    draft_id: str = Field(alias="draftId")
    exported_by: str = Field(alias="exportedBy")
    success: bool
    source_path: str = Field(alias="sourcePath")
    destination_path: str | None = Field(default=None, alias="destinationPath")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: str = Field(alias="createdAt")


class ExportRecordsResponse(ApiModel):
    items: list[ExportRecordItem]
    total: int


class ExportActionResponse(ExportRecordItem):
    pass


class PaperInsightsResponse(ApiModel):
    items: list[PaperInsightItem]
    total: int


class EditorialDraftsResponse(ApiModel):
    items: list[EditorialDraftItem]
    total: int


class NotificationFeedItem(ApiModel):
    notification: NotificationItem
    paper_title: str = Field(alias="paperTitle")
    source: str


class NotificationFeedResponse(ApiModel):
    items: list[NotificationFeedItem]
    total: int
    failed_count: int = Field(alias="failedCount")
    successful_count: int = Field(alias="successfulCount")


class NotificationRetryRequest(ApiModel):
    notification_ids: list[int] | None = Field(default=None, alias="notificationIds")
    paper_ids: list[int] | None = Field(default=None, alias="paperIds")
    destination: str = "feishu"


class NotificationRetryResultItem(ApiModel):
    paper_id: int = Field(alias="paperId")
    title: str
    destination: str
    success: bool
    error_message: str | None = Field(default=None, alias="errorMessage")


class NotificationRetryResponse(ApiModel):
    items: list[NotificationRetryResultItem]
    requested: int
    attempted: int
    succeeded: int
    failed: int


class SourceHealthItem(ApiModel):
    source: str
    enabled: bool
    status: str
    last_run_at: str = Field(alias="lastRunAt")
    fetched_count: int = Field(alias="fetchedCount")
    new_count: int = Field(alias="newCount")
    notes: str


class PipelineStageItem(ApiModel):
    stage_id: str = Field(alias="stageId")
    name: str
    status: str
    summary: str
    implemented_in: list[str] = Field(alias="implementedIn")
    evidence: str


class PipelineSummaryMetrics(ApiModel):
    total_papers: int = Field(alias="totalPapers")
    papers_with_insights: int = Field(alias="papersWithInsights")
    pending_notifications: int = Field(alias="pendingNotifications")
    editorial_drafts: int = Field(alias="editorialDrafts")


class PipelineSummaryResponse(ApiModel):
    metrics: PipelineSummaryMetrics
    stages: list[PipelineStageItem]
    source_health: list[SourceHealthItem] = Field(alias="sourceHealth")


class CrawlRunItem(ApiModel):
    run_id: int = Field(alias="runId")
    source: str
    status: str
    fetched_count: int = Field(alias="fetchedCount")
    new_count: int = Field(alias="newCount")
    error_message: str | None = Field(default=None, alias="errorMessage")
    started_at: str = Field(alias="startedAt")
    finished_at: str | None = Field(default=None, alias="finishedAt")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")


class CrawlRunsResponse(ApiModel):
    items: list[CrawlRunItem]
    total: int


class SummarizationRunItem(ApiModel):
    run_id: int = Field(alias="runId")
    status: str
    papers_processed: int = Field(alias="papersProcessed")
    insights_generated: int = Field(alias="insightsGenerated")
    error_message: str | None = Field(default=None, alias="errorMessage")
    started_at: str = Field(alias="startedAt")
    finished_at: str | None = Field(default=None, alias="finishedAt")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")


class SummarizationRunsResponse(ApiModel):
    items: list[SummarizationRunItem]
    total: int


class EditorialRunItem(ApiModel):
    run_id: int = Field(alias="runId")
    status: str
    papers_processed: int = Field(alias="papersProcessed")
    drafts_generated: int = Field(alias="draftsGenerated")
    error_message: str | None = Field(default=None, alias="errorMessage")
    started_at: str = Field(alias="startedAt")
    finished_at: str | None = Field(default=None, alias="finishedAt")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")


class EditorialRunsResponse(ApiModel):
    items: list[EditorialRunItem]
    total: int


def create_envelope(data: T) -> ApiEnvelope[T]:
    return ApiEnvelope(
        data=data,
        meta=ApiMeta(generated_at=utc_now()),
    )
