import assert from "node:assert/strict";
import test from "node:test";

import {
  API_SCHEMA_VERSION,
  createApiEnvelope,
  createApiMeta,
  type NotificationFeedResponse,
  type PaperDetailResponse,
  type PapersListResponse,
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
