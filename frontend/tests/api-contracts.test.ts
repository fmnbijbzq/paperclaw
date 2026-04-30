import assert from "node:assert/strict";
import test from "node:test";

import {
  API_SCHEMA_VERSION,
  createApiEnvelope,
  createApiMeta,
  type EditorialDraftDetailResponse,
  type EditorialDraftsResponse,
  type ExportActionResponse,
  type ExportRecordsResponse,
  type NotificationFeedResponse,
  type PaperDetailResponse,
  type PapersListResponse,
  type PipelineTaskCreateRequest,
  type PipelineTasksResponse,
  type PipelineSummaryResponse,
} from "../lib/api-contracts.ts";

test("createApiMeta and createApiEnvelope stamp future API responses with stable metadata", () => {
  const papersResponse: PapersListResponse = {
    items: [
      {
        paper: {
          paperId: 42,
          sourcePaperId: "arxiv-2404.0042",
          title: "Graph Executors for Paper Ops",
          abstract: "A test fixture for API contract coverage.",
          authors: ["A. Researcher"],
          source: "arxiv",
          venue: "arXiv",
          categories: ["agents"],
          paperUrl: "https://example.com/papers/42",
          pdfUrl: "https://example.com/papers/42.pdf",
          publishedAt: "2026-04-26T10:00:00Z",
          updatedAtSource: "2026-04-26T10:00:00Z",
        },
        insight: {
          insightId: 7,
          summaryShort: "Structured execution graphs keep recovery visible.",
          confidenceScore: 0.91,
          updatedAt: "2026-04-26T11:00:00Z",
        },
        notificationSummary: {
          totalAttempts: 2,
          latestStatus: "failed",
          lastSentAt: "2026-04-26T11:10:00Z",
        },
        editorialDraftCount: 3,
      },
    ],
    total: 1,
    appliedQuery: "graph",
  };

  const meta = createApiMeta({
    dataSource: "demo",
    generatedAt: "2026-04-27T00:00:00Z",
  });
  const envelope = createApiEnvelope(papersResponse, {
    dataSource: "demo",
    generatedAt: meta.generatedAt,
  });

  assert.equal(meta.schemaVersion, API_SCHEMA_VERSION);
  assert.equal(meta.generatedAt, "2026-04-27T00:00:00Z");
  assert.equal(envelope.meta.dataSource, "demo");
  assert.equal(envelope.data.items[0]?.notificationSummary.latestStatus, "failed");
});

test("paper detail, pipeline, and notification contracts cover the current frontend needs", () => {
  const detailResponse: PaperDetailResponse = {
    record: null,
  };
  const pipelineResponse: PipelineSummaryResponse = {
    metrics: {
      totalPapers: 6,
      papersWithInsights: 4,
      pendingNotifications: 2,
      editorialDrafts: 6,
    },
    stages: [],
    sourceHealth: [],
  };
  const notificationResponse: NotificationFeedResponse = {
    items: [],
    total: 0,
    failedCount: 0,
    successfulCount: 0,
  };

  assert.equal(detailResponse.record, null);
  assert.deepEqual(Object.keys(pipelineResponse.metrics), [
    "totalPapers",
    "papersWithInsights",
    "pendingNotifications",
    "editorialDrafts",
  ]);
  assert.equal(notificationResponse.total, 0);
});

test("pipeline task contracts cover asynchronous workflow control", () => {
  const request: PipelineTaskCreateRequest = {
    taskType: "full_pipeline",
    requestedBy: "operator",
    notify: true,
    editorialLimit: 3,
  };
  const response: PipelineTasksResponse = {
    items: [
      {
        taskId: 101,
        taskType: "full_pipeline",
        status: "running",
        currentStage: "crawl",
        progressCurrent: 1,
        progressTotal: 3,
        requestedBy: "operator",
        parameters: { notify: true, editorialLimit: 3 },
        result: {
          crawl: {
            totalFetched: 12,
            totalNew: 4,
          },
        },
        errorMessage: null,
        createdAt: "2026-04-30T12:00:00Z",
        startedAt: "2026-04-30T12:00:03Z",
        finishedAt: null,
      },
    ],
    total: 1,
  };

  assert.equal(request.taskType, "full_pipeline");
  assert.equal(response.items[0]?.currentStage, "crawl");
});

test("draft and export contracts cover operational workflow pages", () => {
  const draftsResponse: EditorialDraftsResponse = {
    items: [
      {
        draftId: "draft-42-a",
        paperId: 42,
        platform: "bilibili",
        title: "Paper ops recap",
        hook: "Why review state needs to stay explicit.",
        status: "approved",
        assignee: "A. Editor",
        updatedAt: "2026-04-28T12:00:00Z",
        outputPath: "outputs/editorial/2026-04-28/paper-ops-recap.md",
      },
    ],
    total: 1,
  };
  const draftDetailResponse: EditorialDraftDetailResponse = {
    ...draftsResponse.items[0]!,
    markdownContent: "# Paper ops recap\n\n- Review\n- Approve\n- Export",
    reviewNote: "Ready for publishing.",
    paper: {
      paperId: 42,
      sourcePaperId: "arxiv-2404.0042",
      title: "Graph Executors for Paper Ops",
      abstract: "A test fixture for draft detail coverage.",
      authors: ["A. Researcher"],
      source: "arxiv",
      venue: "arXiv",
      categories: ["agents"],
      paperUrl: "https://example.com/papers/42",
      pdfUrl: "https://example.com/papers/42.pdf",
      publishedAt: "2026-04-26T10:00:00Z",
      updatedAtSource: "2026-04-26T10:00:00Z",
    },
  };
  const exportRecordsResponse: ExportRecordsResponse = {
    items: [
      {
        exportId: 11,
        draftId: "draft-42-a",
        exportedBy: "ops-bot",
        success: true,
        sourcePath: "outputs/editorial/2026-04-28/paper-ops-recap.md",
        destinationPath: "outputs/exported/2026-04-28/paper-ops-recap.md",
        errorMessage: null,
        createdAt: "2026-04-28T13:00:00Z",
      },
    ],
    total: 1,
  };
  const exportActionResponse: ExportActionResponse = exportRecordsResponse.items[0]!;

  assert.equal(draftDetailResponse.paper.paperId, 42);
  assert.match(draftDetailResponse.markdownContent, /^#/);
  assert.equal(exportActionResponse.success, true);
  assert.equal(exportRecordsResponse.total, 1);
});
