import assert from "node:assert/strict";
import test from "node:test";

import { createNotificationsRepository } from "../lib/repositories/notifications.ts";
import { createPapersRepository } from "../lib/repositories/papers.ts";
import { createPipelineRepository } from "../lib/repositories/pipeline.ts";
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
  const matches = await repository.search("prompt efficient");

  assert.deepEqual(
    records.map((record) => record.paper.paperId),
    [2, 1],
  );
  assert.equal(records[1]?.insight?.insightId, 9);
  assert.deepEqual(
    records[1]?.editorialDrafts.map((draft) => draft.draftId),
    ["1-b", "1-a"],
  );
  assert.equal(matches.length, 1);
  assert.equal(matches[0]?.paper.paperId, 1);
  assert.equal(await repository.getRecord(999), null);
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
  } satisfies PipelineDataSource);

  const stages = await repository.listStages();
  const sourceHealth = await repository.getSourceHealthBySource("cvf");

  assert.equal(stages[0]?.stageId, "fetch");
  assert.equal(sourceHealth?.status, "degraded");
  assert.equal(await repository.getSourceHealthBySource("arxiv"), null);
});
