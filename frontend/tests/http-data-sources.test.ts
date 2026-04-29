import assert from "node:assert/strict";
import test from "node:test";

import { createApiEnvelope, type EditorialDraftsResponse, type PaperInsightsResponse } from "../lib/api-contracts.ts";
import { createHttpDraftsDataSource } from "../lib/data-sources/http/drafts.ts";
import { createHttpExportsDataSource } from "../lib/data-sources/http/exports.ts";
import { createHttpNotificationsDataSource } from "../lib/data-sources/http/notifications.ts";
import { createHttpPapersDataSource } from "../lib/data-sources/http/papers.ts";
import { buildRequestUrl, type FetchLike } from "../lib/data-sources/http/shared.ts";
import { createHttpPipelineDataSource } from "../lib/data-sources/http/pipeline.ts";

interface MockRoute {
  body: unknown;
  method?: string;
  status?: number;
}

function createFetchStub(
  routes: Record<string, MockRoute>,
): {
  calls: string[];
  fetch: FetchLike;
  requests: Array<{
    body?: string;
    method: string;
    url: string;
  }>;
} {
  const calls: string[] = [];
  const requests: Array<{
    body?: string;
    method: string;
    url: string;
  }> = [];

  return {
    calls,
    requests,
    fetch: async (input) => {
      const url = String(input);
      const method = "GET";
      const route = routes[`${method} ${url}`] ?? routes[url];

      calls.push(url);
      requests.push({
        method,
        url,
      });

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

test("HTTP papers data source forwards advanced search filters and pagination", async () => {
  const { calls, fetch } = createFetchStub({
    "GET https://paperclaw.example/api/papers?q=graph&source=openreview&category=agents&venue=ICLR%202026&hasInsight=true&hasDraft=false&limit=25&offset=25":
      {
        body: createApiEnvelope({
          items: [
            {
              paper: {
                paperId: 21,
                sourcePaperId: "or-iclr26-graph-executor",
                title: "Structured review loops for paper operations",
                abstract: "Advanced search fixture.",
                authors: ["A. Researcher"],
                source: "openreview",
                venue: "ICLR 2026",
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
          total: 41,
          appliedQuery: "graph",
        }),
      },
  });
  const dataSource = createHttpPapersDataSource({
    baseUrl: "https://paperclaw.example/api/",
    fetch,
  });

  const result = await dataSource.searchPapers({
    q: "graph",
    source: "openreview",
    category: "agents",
    venue: "ICLR 2026",
    hasInsight: true,
    hasDraft: false,
    page: 2,
    pageSize: 25,
  });

  assert.equal(result.total, 41);
  assert.equal(result.items[0]?.paperId, 21);
  assert.deepEqual(calls, [
    "https://paperclaw.example/api/papers?q=graph&source=openreview&category=agents&venue=ICLR%202026&hasInsight=true&hasDraft=false&limit=25&offset=25",
  ]);
});

test("HTTP drafts and exports data sources map detail payloads and workflow actions", async () => {
  const requests: Array<{
    body?: string;
    method: string;
    url: string;
  }> = [];
  const fetch: FetchLike = async (input, init) => {
    const url = String(input);
    const method = init?.method?.toUpperCase() ?? "GET";
    const body = typeof init?.body === "string" ? init.body : undefined;

    requests.push({
      body,
      method,
      url,
    });

    const routes: Record<string, unknown> = {
      "GET https://paperclaw.example/api/drafts?status=approved&platform=bilibili&limit=5": createApiEnvelope<EditorialDraftsResponse>({
        items: [
          {
            draftId: "draft-21-a",
            paperId: 21,
            platform: "bilibili",
            title: "Review loop summary",
            hook: "Why visibility matters",
            status: "approved",
            assignee: "Nina",
            updatedAt: "2026-04-28T09:20:00Z",
            outputPath: "outputs/draft-21-a.md",
          },
        ],
        total: 1,
      }),
      "GET https://paperclaw.example/api/drafts/draft-21-a": createApiEnvelope({
        draftId: "draft-21-a",
        paperId: 21,
        platform: "bilibili",
        title: "Review loop summary",
        hook: "Why visibility matters",
        status: "approved",
        assignee: "Nina",
        updatedAt: "2026-04-28T09:20:00Z",
        outputPath: "outputs/draft-21-a.md",
        markdownContent: "# Review loop summary",
        reviewNote: "Approved for export.",
        paper: {
          paperId: 21,
          sourcePaperId: "or-iclr26-graph-executor",
          title: "Structured review loops for paper operations",
          abstract: "Advanced search fixture.",
          authors: ["A. Researcher"],
          source: "openreview",
          venue: "ICLR 2026",
          categories: ["agents"],
          paperUrl: "https://example.com/papers/21",
          pdfUrl: "https://example.com/papers/21.pdf",
          publishedAt: "2026-04-28T08:00:00Z",
          updatedAtSource: "2026-04-28T08:00:00Z",
        },
      }),
      "POST https://paperclaw.example/api/drafts/draft-21-a/review": createApiEnvelope({
        draftId: "draft-21-a",
        paperId: 21,
        platform: "bilibili",
        title: "Review loop summary",
        hook: "Why visibility matters",
        status: "in_review",
        assignee: "Nina",
        updatedAt: "2026-04-28T09:35:00Z",
        outputPath: "outputs/draft-21-a.md",
        markdownContent: "# Review loop summary",
        reviewNote: "Ready for human review.",
        paper: {
          paperId: 21,
          sourcePaperId: "or-iclr26-graph-executor",
          title: "Structured review loops for paper operations",
          abstract: "Advanced search fixture.",
          authors: ["A. Researcher"],
          source: "openreview",
          venue: "ICLR 2026",
          categories: ["agents"],
          paperUrl: "https://example.com/papers/21",
          pdfUrl: "https://example.com/papers/21.pdf",
          publishedAt: "2026-04-28T08:00:00Z",
          updatedAtSource: "2026-04-28T08:00:00Z",
        },
      }),
      "POST https://paperclaw.example/api/drafts/draft-21-a/export": createApiEnvelope({
        exportId: 14,
        draftId: "draft-21-a",
        exportedBy: "ops-bot",
        success: true,
        sourcePath: "outputs/draft-21-a.md",
        destinationPath: "outputs/exported/draft-21-a.md",
        errorMessage: null,
        createdAt: "2026-04-28T09:40:00Z",
      }),
      "GET https://paperclaw.example/api/exports": createApiEnvelope({
        items: [
          {
            exportId: 14,
            draftId: "draft-21-a",
            exportedBy: "ops-bot",
            success: true,
            sourcePath: "outputs/draft-21-a.md",
            destinationPath: "outputs/exported/draft-21-a.md",
            errorMessage: null,
            createdAt: "2026-04-28T09:40:00Z",
          },
        ],
        total: 1,
      }),
    };

    const routeKey = `${method} ${url}`;
    const route = routes[routeKey];

    if (!route) {
      throw new Error(`Unexpected request: ${routeKey}`);
    }

    return {
      ok: true,
      status: 200,
      async json() {
        return route;
      },
    };
  };
  const draftsDataSource = createHttpDraftsDataSource({
    baseUrl: "https://paperclaw.example/api",
    fetch,
  });
  const exportsDataSource = createHttpExportsDataSource({
    baseUrl: "https://paperclaw.example/api",
    fetch,
  });

  const [drafts, detail, reviewedDraft, exportRecord, exportRecords] = await Promise.all([
    draftsDataSource.listDrafts({
      status: "approved",
      platform: "bilibili",
      limit: 5,
    }),
    draftsDataSource.getDraftDetail("draft-21-a"),
    draftsDataSource.reviewDraft("draft-21-a", {
      actor: "editor-1",
      note: "Ready for human review.",
    }),
    draftsDataSource.exportDraft("draft-21-a", {
      exportedBy: "ops-bot",
    }),
    exportsDataSource.listExportRecords(),
  ]);

  assert.equal(drafts[0]?.draftId, "draft-21-a");
  assert.equal(detail?.paper.paperId, 21);
  assert.equal(reviewedDraft.status, "in_review");
  assert.equal(exportRecord.exportId, 14);
  assert.equal(exportRecords[0]?.draftId, "draft-21-a");
  assert.deepEqual(
    requests.map(({ method, url }) => `${method} ${url}`),
    [
      "GET https://paperclaw.example/api/drafts?status=approved&platform=bilibili&limit=5",
      "GET https://paperclaw.example/api/drafts/draft-21-a",
      "POST https://paperclaw.example/api/drafts/draft-21-a/review",
      "POST https://paperclaw.example/api/drafts/draft-21-a/export",
      "GET https://paperclaw.example/api/exports",
    ],
  );
  assert.deepEqual(JSON.parse(requests[2]?.body ?? "{}"), {
    actor: "editor-1",
    note: "Ready for human review.",
  });
  assert.deepEqual(JSON.parse(requests[3]?.body ?? "{}"), {
    exportedBy: "ops-bot",
  });
});
