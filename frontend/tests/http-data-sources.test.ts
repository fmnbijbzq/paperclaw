import assert from "node:assert/strict";
import test from "node:test";

import { createApiEnvelope, type EditorialDraftsResponse, type PaperInsightsResponse } from "../lib/api-contracts.ts";
import { createHttpNotificationsDataSource } from "../lib/data-sources/http/notifications.ts";
import { createHttpPapersDataSource } from "../lib/data-sources/http/papers.ts";
import { buildRequestUrl, type FetchLike } from "../lib/data-sources/http/shared.ts";
import { createHttpPipelineDataSource } from "../lib/data-sources/http/pipeline.ts";

interface MockRoute {
  body: unknown;
  status?: number;
}

function createFetchStub(routes: Record<string, MockRoute>): { calls: string[]; fetch: FetchLike } {
  const calls: string[] = [];

  return {
    calls,
    fetch: async (input) => {
      const url = String(input);
      const route = routes[url];

      calls.push(url);

      if (!route) {
        throw new Error(`Unexpected request: ${url}`);
      }

      const status = route.status ?? 200;

      return {
        ok: status >= 200 && status < 300,
        status,
        async json() {
          return route.body;
        },
      };
    },
  };
}

test("buildRequestUrl joins base URLs, paths, and query params without double slashes", () => {
  const requestUrl = buildRequestUrl("https://paperclaw.example/api/", "/notifications", {
    limit: 25,
    onlyFailed: true,
  });

  assert.equal(requestUrl, "https://paperclaw.example/api/notifications?limit=25&onlyFailed=true");
});

test("HTTP papers data source maps contract responses into repository-facing collections", async () => {
  const { calls, fetch } = createFetchStub({
    "https://paperclaw.example/api/papers": {
      body: createApiEnvelope({
        items: [
          {
            paper: {
              paperId: 21,
              sourcePaperId: "arxiv-2501.0021",
              title: "Structured review loops for paper operations",
              abstract: "A fixture for the HTTP papers data source.",
              authors: ["A. Researcher"],
              source: "arxiv",
              venue: "arXiv",
              categories: ["agents"],
              paperUrl: "https://example.com/papers/21",
              pdfUrl: "https://example.com/papers/21.pdf",
              publishedAt: "2026-04-28T08:00:00Z",
              updatedAtSource: "2026-04-28T08:00:00Z",
            },
            insight: {
              insightId: 4,
              summaryShort: "Reasoning traces increase operator confidence.",
              confidenceScore: 0.97,
              updatedAt: "2026-04-28T09:00:00Z",
            },
            notificationSummary: {
              totalAttempts: 1,
              latestStatus: "delivered",
              lastSentAt: "2026-04-28T09:10:00Z",
            },
            editorialDraftCount: 2,
          },
        ],
        total: 1,
        appliedQuery: "",
      }),
    },
    "https://paperclaw.example/api/papers/insights": {
      body: createApiEnvelope<PaperInsightsResponse>({
        items: [
          {
            insightId: 4,
            paperId: 21,
            summaryShort: "Reasoning traces increase operator confidence.",
            summaryLong: "Long-form insight body.",
            noveltyPoints: ["Clear execution visibility."],
            limitations: ["Depends on disciplined tooling."],
            applications: ["Research operations dashboards."],
            confidenceScore: 0.97,
            updatedAt: "2026-04-28T09:00:00Z",
          },
        ],
        total: 1,
      }),
    },
    "https://paperclaw.example/api/papers/editorial-drafts": {
      body: createApiEnvelope<EditorialDraftsResponse>({
        items: [
          {
            draftId: "draft-21-a",
            paperId: 21,
            platform: "bilibili",
            title: "Review loop summary",
            hook: "Why visibility matters",
            status: "reviewed",
            updatedAt: "2026-04-28T09:20:00Z",
            outputPath: "outputs/draft-21-a.md",
          },
        ],
        total: 1,
      }),
    },
  });
  const dataSource = createHttpPapersDataSource({
    baseUrl: "https://paperclaw.example/api/",
    fetch,
  });

  const [papers, insights, editorialDrafts] = await Promise.all([
    dataSource.listPapers(),
    dataSource.listInsights(),
    dataSource.listEditorialDrafts(),
  ]);

  assert.equal(papers[0]?.paperId, 21);
  assert.equal(insights[0]?.summaryLong, "Long-form insight body.");
  assert.equal(editorialDrafts[0]?.draftId, "draft-21-a");
  assert.deepEqual(calls, [
    "https://paperclaw.example/api/papers",
    "https://paperclaw.example/api/papers/insights",
    "https://paperclaw.example/api/papers/editorial-drafts",
  ]);
});

test("HTTP notifications data source unwraps feed contracts to raw notification items", async () => {
  const { fetch } = createFetchStub({
    "https://paperclaw.example/api/notifications": {
      body: createApiEnvelope({
        items: [
          {
            notification: {
              notificationId: 61,
              destination: "feishu",
              paperId: 21,
              success: false,
              errorMessage: "Retry scheduled",
              sentAt: "2026-04-28T10:00:00Z",
            },
            paperTitle: "Structured review loops for paper operations",
            source: "arxiv",
          },
        ],
        total: 1,
        failedCount: 1,
        successfulCount: 0,
      }),
    },
  });
  const dataSource = createHttpNotificationsDataSource({
    baseUrl: "https://paperclaw.example/api",
    fetch,
  });

  const notifications = await dataSource.listNotifications();

  assert.deepEqual(notifications, [
    {
      notificationId: 61,
      destination: "feishu",
      paperId: 21,
      success: false,
      errorMessage: "Retry scheduled",
      sentAt: "2026-04-28T10:00:00Z",
    },
  ]);
});

test("HTTP pipeline data source maps summary payloads to stages and source health", async () => {
  const { calls, fetch } = createFetchStub({
    "https://paperclaw.example/api/pipeline/summary": {
      body: createApiEnvelope({
        metrics: {
          totalPapers: 12,
          papersWithInsights: 7,
          pendingNotifications: 3,
          editorialDrafts: 5,
        },
        stages: [
          {
            stageId: "notify",
            name: "Notify",
            status: "partial",
            summary: "Delivery retries remain visible.",
            implementedIn: ["run_notify_once.py"],
            evidence: "The retry loop exists in the backend.",
          },
        ],
        sourceHealth: [
          {
            source: "cvf",
            enabled: true,
            status: "healthy",
            lastRunAt: "2026-04-28T08:00:00Z",
            fetchedCount: 14,
            newCount: 3,
            notes: "Latest run completed cleanly.",
          },
        ],
      }),
    },
  });
  const dataSource = createHttpPipelineDataSource({
    baseUrl: "https://paperclaw.example/api",
    fetch,
  });

  const [stages, sourceHealth] = await Promise.all([
    dataSource.listPipelineStages(),
    dataSource.listSourceHealth(),
  ]);

  assert.equal(stages[0]?.stageId, "notify");
  assert.equal(sourceHealth[0]?.source, "cvf");
  assert.deepEqual(calls, [
    "https://paperclaw.example/api/pipeline/summary",
    "https://paperclaw.example/api/pipeline/summary",
  ]);
});

test("HTTP data sources reject malformed API envelopes", async () => {
  const { fetch } = createFetchStub({
    "https://paperclaw.example/api/notifications": {
      body: {
        items: [],
      },
    },
  });
  const dataSource = createHttpNotificationsDataSource({
    baseUrl: "https://paperclaw.example/api",
    fetch,
  });

  await assert.rejects(() => dataSource.listNotifications(), /Invalid API envelope/i);
});
