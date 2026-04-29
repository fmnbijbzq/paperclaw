import assert from "node:assert/strict";
import test from "node:test";

import { createDraftsRepository } from "../lib/repositories/drafts.ts";
import { createExportsRepository } from "../lib/repositories/exports.ts";
import { createNotificationsRepository } from "../lib/repositories/notifications.ts";
import { createPapersRepository } from "../lib/repositories/papers.ts";
import { createPipelineRepository } from "../lib/repositories/pipeline.ts";
import type { DraftsDataSource } from "../lib/data-sources/demo/drafts.ts";
import type { ExportsDataSource } from "../lib/data-sources/demo/exports.ts";
import type { NotificationsDataSource } from "../lib/data-sources/demo/notifications.ts";
import type { PapersDataSource } from "../lib/data-sources/demo/papers.ts";
import type { PipelineDataSource } from "../lib/data-sources/demo/pipeline.ts";

test("papers repository composes sorted records and search-ready summaries", async () => {
  const repository = createPapersRepository({
    async listPapers() {
      return [
        {
          paperId: 1,
          sourcePaperId: "alpha",
          title: "Sparse prompts",
          abstract: "Prompt efficient scene labeling.",
          authors: ["Ada Lovelace"],
          source: "arxiv",
          venue: "arXiv",
          categories: ["vision"],
          paperUrl: "https://example.com/alpha",
          pdfUrl: "https://example.com/alpha.pdf",
          publishedAt: "2026-04-24T10:00:00Z",
          updatedAtSource: "2026-04-24T10:00:00Z",
        },
        {
          paperId: 2,
          sourcePaperId: "beta",
          title: "Robot failure indexes",
          abstract: "Operational retrieval anchors for drift analysis.",
          authors: ["Grace Hopper"],
          source: "cvf",
          venue: "CVPR 2026",
          categories: ["robotics"],
          paperUrl: "https://example.com/beta",
          pdfUrl: "https://example.com/beta.pdf",
          publishedAt: "2026-04-26T10:00:00Z",
          updatedAtSource: "2026-04-26T10:00:00Z",
        },
      ];
    },
    async listInsights() {
      return [
        {
          insightId: 9,
          paperId: 1,
          summaryShort: "Prompt efficient reconstruction is the key result.",
          summaryLong: "Long summary",
          noveltyPoints: [],
          limitations: [],
          applications: [],
          confidenceScore: 0.94,
          updatedAt: "2026-04-24T12:00:00Z",
        },
      ];
    },
    async listEditorialDrafts() {
      return [
        {
          draftId: "1-b",
          paperId: 1,
          platform: "bilibili",
          title: "Second draft",
          hook: "Hook",
          status: "reviewed",
          updatedAt: "2026-04-24T14:00:00Z",
          outputPath: "outputs/1-b.md",
        },
        {
          draftId: "1-a",
          paperId: 1,
          platform: "douyin",
          title: "First draft",
          hook: "Hook",
          status: "generated",
          updatedAt: "2026-04-24T11:00:00Z",
          outputPath: "outputs/1-a.md",
        },
      ];
    },
  } satisfies PapersDataSource);

  const records = await repository.listRecords();
  const matches = await repository.search({
    q: "prompt efficient",
    hasInsight: true,
    page: 1,
    pageSize: 20,
  });

  assert.deepEqual(
    records.map((record) => record.paper.paperId),
    [2, 1],
  );
  assert.equal(records[1]?.insight?.insightId, 9);
  assert.deepEqual(
    records[1]?.editorialDrafts.map((draft) => draft.draftId),
    ["1-b", "1-a"],
  );
  assert.equal(matches.total, 1);
  assert.equal(matches.records.length, 1);
  assert.equal(matches.records[0]?.paper.paperId, 1);
  assert.equal(await repository.getRecord(999), null);
});

test("papers repository applies advanced filters and pagination for search results", async () => {
  const repository = createPapersRepository({
    async listPapers() {
      return [
        {
          paperId: 1,
          sourcePaperId: "alpha",
          title: "Sparse prompts",
          abstract: "Prompt efficient scene labeling.",
          authors: ["Ada Lovelace"],
          source: "arxiv",
          venue: "arXiv",
          categories: ["vision", "agents"],
          paperUrl: "https://example.com/alpha",
          pdfUrl: "https://example.com/alpha.pdf",
          publishedAt: "2026-04-24T10:00:00Z",
          updatedAtSource: "2026-04-24T10:00:00Z",
        },
        {
          paperId: 2,
          sourcePaperId: "beta",
          title: "Robot failure indexes",
          abstract: "Operational retrieval anchors for drift analysis.",
          authors: ["Grace Hopper"],
          source: "cvf",
          venue: "CVPR 2026",
          categories: ["robotics"],
          paperUrl: "https://example.com/beta",
          pdfUrl: "https://example.com/beta.pdf",
          publishedAt: "2026-04-26T10:00:00Z",
          updatedAtSource: "2026-04-26T10:00:00Z",
        },
        {
          paperId: 3,
          sourcePaperId: "gamma",
          title: "Agent coordination notes",
          abstract: "Human review keeps state transitions legible.",
          authors: ["Margaret Hamilton"],
          source: "openreview",
          venue: "ICLR 2026",
          categories: ["agents"],
          paperUrl: "https://example.com/gamma",
          pdfUrl: "https://example.com/gamma.pdf",
          publishedAt: "2026-04-27T10:00:00Z",
          updatedAtSource: "2026-04-27T10:00:00Z",
        },
      ];
    },
    async listInsights() {
      return [
        {
          insightId: 9,
          paperId: 1,
          summaryShort: "Prompt efficient reconstruction is the key result.",
          summaryLong: "Long summary",
          noveltyPoints: [],
          limitations: [],
          applications: [],
          confidenceScore: 0.94,
          updatedAt: "2026-04-24T12:00:00Z",
        },
        {
          insightId: 10,
          paperId: 3,
          summaryShort: "Typed review loops stabilize approvals.",
          summaryLong: "Long summary",
          noveltyPoints: [],
          limitations: [],
          applications: [],
          confidenceScore: 0.9,
          updatedAt: "2026-04-27T12:00:00Z",
        },
      ];
    },
    async listEditorialDrafts() {
      return [
        {
          draftId: "1-a",
          paperId: 1,
          platform: "bilibili",
          title: "Draft one",
          hook: "Hook",
          status: "approved",
          assignee: "Nina",
          updatedAt: "2026-04-24T11:00:00Z",
          outputPath: "outputs/1-a.md",
        },
        {
          draftId: "3-a",
          paperId: 3,
          platform: "douyin",
          title: "Draft two",
          hook: "Hook",
          status: "generated",
          assignee: null,
          updatedAt: "2026-04-27T11:00:00Z",
          outputPath: "outputs/3-a.md",
        },
      ];
    },
  } satisfies PapersDataSource);

  const result = await repository.search({
    q: "agent",
    source: "openreview",
    category: "agents",
    venue: "iclr",
    hasInsight: true,
    hasDraft: true,
    page: 1,
    pageSize: 1,
  });

  assert.equal(result.total, 1);
  assert.equal(result.page, 1);
  assert.equal(result.totalPages, 1);
  assert.equal(result.records[0]?.paper.paperId, 3);
});

test("notifications repository sorts the feed newest-first and filters by paper id", async () => {
  const repository = createNotificationsRepository({
    async listNotifications() {
      return [
        {
          notificationId: 11,
          destination: "feishu",
          paperId: 1,
          success: true,
          errorMessage: null,
          sentAt: "2026-04-24T11:00:00Z",
        },
        {
          notificationId: 12,
          destination: "feishu",
          paperId: 2,
          success: false,
          errorMessage: "Timeout",
          sentAt: "2026-04-26T09:00:00Z",
        },
        {
          notificationId: 13,
          destination: "feishu",
          paperId: 1,
          success: false,
          errorMessage: "Retry needed",
          sentAt: "2026-04-25T09:00:00Z",
        },
      ];
    },
  } satisfies NotificationsDataSource);

  const feed = await repository.listFeed();
  const paperNotifications = await repository.listByPaperId(1);

  assert.deepEqual(
    feed.map((notification) => notification.notificationId),
    [12, 13, 11],
  );
  assert.deepEqual(
    paperNotifications.map((notification) => notification.notificationId),
    [13, 11],
  );
});

test("pipeline repository exposes stages and source-health lookups", async () => {
  const repository = createPipelineRepository({
    async listPipelineStages() {
      return [
        {
          stageId: "fetch",
          name: "Fetch",
          status: "live",
          summary: "Crawler input",
          implementedIn: ["app/sources/arxiv.py"],
          evidence: "Ingest is wired up.",
        },
      ];
    },
    async listSourceHealth() {
      return [
        {
          source: "cvf",
          enabled: true,
          status: "degraded",
          lastRunAt: "2026-04-26T09:00:00Z",
          fetchedCount: 12,
          newCount: 2,
          notes: "Retry batch still pending.",
        },
      ];
    },
    async listCrawlRuns() {
      return [];
    },
    async listSummarizationRuns() {
      return [];
    },
    async listEditorialRuns() {
      return [];
    },
  } satisfies PipelineDataSource);

  const stages = await repository.listStages();
  const sourceHealth = await repository.getSourceHealthBySource("cvf");

  assert.equal(stages[0]?.stageId, "fetch");
  assert.equal(sourceHealth?.status, "degraded");
  assert.equal(await repository.getSourceHealthBySource("arxiv"), null);
});

test("pipeline repository exposes run lists", async () => {
  const repository = createPipelineRepository({
    async listPipelineStages() {
      return [];
    },
    async listSourceHealth() {
      return [];
    },
    async listCrawlRuns() {
      return [
        {
          runId: 1,
          source: "arxiv",
          status: "success",
          fetchedCount: 10,
          newCount: 3,
          errorMessage: null,
          startedAt: "2026-04-26T06:00:00Z",
          finishedAt: "2026-04-26T06:05:00Z",
          durationSeconds: 300,
        },
      ];
    },
    async listSummarizationRuns() {
      return [
        {
          runId: 1,
          status: "success",
          papersProcessed: 10,
          insightsGenerated: 10,
          errorMessage: null,
          startedAt: "2026-04-26T06:05:00Z",
          finishedAt: "2026-04-26T06:07:00Z",
          durationSeconds: 120,
        },
      ];
    },
    async listEditorialRuns() {
      return [];
    },
  } satisfies PipelineDataSource);

  const crawlRuns = await repository.listCrawlRuns();
  assert.equal(crawlRuns.length, 1);
  assert.equal(crawlRuns[0]?.source, "arxiv");
  assert.equal(crawlRuns[0]?.status, "success");

  const sumRuns = await repository.listSummarizationRuns();
  assert.equal(sumRuns.length, 1);
  assert.equal(sumRuns[0]?.papersProcessed, 10);
});

test("drafts repository sorts, filters, and exposes workflow mutations", async () => {
  const repository = createDraftsRepository({
    async listDrafts() {
      return [
        {
          draftId: "draft-1",
          paperId: 1,
          platform: "bilibili",
          title: "Latest approved draft",
          hook: "Hook",
          status: "approved",
          assignee: "Nina",
          updatedAt: "2026-04-27T09:00:00Z",
          outputPath: "outputs/draft-1.md",
        },
        {
          draftId: "draft-2",
          paperId: 2,
          platform: "xiaohongshu",
          title: "In review draft",
          hook: "Hook",
          status: "in_review",
          assignee: "Kai",
          updatedAt: "2026-04-26T09:00:00Z",
          outputPath: "outputs/draft-2.md",
        },
        {
          draftId: "draft-3",
          paperId: 3,
          platform: "bilibili",
          title: "Generated draft",
          hook: "Hook",
          status: "generated",
          assignee: null,
          updatedAt: "2026-04-25T09:00:00Z",
          outputPath: "outputs/draft-3.md",
        },
      ];
    },
    async getDraftDetail(draftId) {
      if (draftId !== "draft-1") {
        return null;
      }

      return {
        draftId: "draft-1",
        paperId: 1,
        platform: "bilibili",
        title: "Latest approved draft",
        hook: "Hook",
        status: "approved",
        assignee: "Nina",
        updatedAt: "2026-04-27T09:00:00Z",
        outputPath: "outputs/draft-1.md",
        markdownContent: "# Draft",
        reviewNote: "Approved for export.",
        paper: {
          paperId: 1,
          sourcePaperId: "alpha",
          title: "Sparse prompts",
          abstract: "Prompt efficient scene labeling.",
          authors: ["Ada Lovelace"],
          source: "arxiv",
          venue: "arXiv",
          categories: ["vision"],
          paperUrl: "https://example.com/alpha",
          pdfUrl: "https://example.com/alpha.pdf",
          publishedAt: "2026-04-24T10:00:00Z",
          updatedAtSource: "2026-04-24T10:00:00Z",
        },
      };
    },
    async reviewDraft() {
      throw new Error("not used in this test");
    },
    async approveDraft(draftId, payload) {
      return {
        draftId,
        paperId: 1,
        platform: "bilibili",
        title: "Latest approved draft",
        hook: "Hook",
        status: "approved",
        assignee: "Nina",
        updatedAt: "2026-04-27T09:00:00Z",
        outputPath: "outputs/draft-1.md",
        markdownContent: payload.note ?? "",
        reviewNote: payload.note ?? null,
        paper: {
          paperId: 1,
          sourcePaperId: "alpha",
          title: "Sparse prompts",
          abstract: "Prompt efficient scene labeling.",
          authors: ["Ada Lovelace"],
          source: "arxiv",
          venue: "arXiv",
          categories: ["vision"],
          paperUrl: "https://example.com/alpha",
          pdfUrl: "https://example.com/alpha.pdf",
          publishedAt: "2026-04-24T10:00:00Z",
          updatedAtSource: "2026-04-24T10:00:00Z",
        },
      };
    },
    async rejectDraft() {
      throw new Error("not used in this test");
    },
    async assignDraft() {
      throw new Error("not used in this test");
    },
    async exportDraft() {
      throw new Error("not used in this test");
    },
  } satisfies DraftsDataSource);

  const bilibiliDrafts = await repository.listDrafts({
    platform: "bilibili",
  });
  const approvedDrafts = await repository.listDrafts({
    status: "approved",
  });
  const approvedDetail = await repository.getDraftDetail("draft-1");
  const approvedAgain = await repository.approveDraft("draft-1", {
    actor: "editor-1",
    note: "Ship it.",
  });

  assert.deepEqual(
    bilibiliDrafts.map((draft) => draft.draftId),
    ["draft-1", "draft-3"],
  );
  assert.deepEqual(
    approvedDrafts.map((draft) => draft.draftId),
    ["draft-1"],
  );
  assert.equal(approvedDetail?.paper.paperId, 1);
  assert.equal(approvedAgain.reviewNote, "Ship it.");
});

test("exports repository sorts newest records first", async () => {
  const repository = createExportsRepository({
    async listExportRecords() {
      return [
        {
          exportId: 1,
          draftId: "draft-1",
          exportedBy: "ops-a",
          success: true,
          sourcePath: "outputs/draft-1.md",
          destinationPath: "outputs/exported/draft-1.md",
          errorMessage: null,
          createdAt: "2026-04-26T08:00:00Z",
        },
        {
          exportId: 2,
          draftId: "draft-2",
          exportedBy: "ops-b",
          success: false,
          sourcePath: "outputs/draft-2.md",
          destinationPath: null,
          errorMessage: "Approval missing",
          createdAt: "2026-04-27T08:00:00Z",
        },
      ];
    },
  } satisfies ExportsDataSource);

  const records = await repository.listExportRecords();

  assert.deepEqual(
    records.map((record) => record.exportId),
    [2, 1],
  );
});
