import assert from "node:assert/strict";
import test from "node:test";

import {
  getDashboardSnapshot,
  getDraftDetail,
  getDraftList,
  getExportRecords,
  getNotificationFeed,
  getPaperDetail,
  searchPapers,
} from "../lib/queries.ts";

test("getDashboardSnapshot derives overview metrics from demo data", async () => {
  const snapshot = await getDashboardSnapshot();

  assert.equal(snapshot.metrics.totalPapers.value, 6);
  assert.equal(snapshot.metrics.papersWithInsights.value, 4);
  assert.equal(snapshot.metrics.pendingNotifications.value, 2);
  assert.equal(snapshot.metrics.editorialDrafts.value, 6);
  assert.equal(snapshot.recentPapers[0]?.paper.paperId, 106);
});

test("searchPapers matches titles, authors, and categories", async () => {
  const titleMatches = await searchPapers({
    q: "Gaussian",
  });
  const authorMatches = await searchPapers({
    q: "Mei Chen",
  });
  const categoryMatches = await searchPapers({
    category: "video",
    page: 1,
    pageSize: 10,
  });

  assert.equal(titleMatches.total, 1);
  assert.match(titleMatches.records[0]?.paper.title ?? "", /Gaussian/i);
  assert.equal(authorMatches.records[0]?.paper.paperId, 105);
  assert.equal(categoryMatches.total, 2);
});

test("getPaperDetail aggregates insight, notification, and editorial draft state", async () => {
  const detail = await getPaperDetail(101);

  assert.ok(detail);
  assert.equal(detail?.insight?.confidenceScore, 0.92);
  assert.equal(detail?.notifications.length, 1);
  assert.equal(detail?.editorialDrafts.length, 3);
  assert.equal(await getPaperDetail(999), null);
});

test("getNotificationFeed keeps the newest delivery attempts first", async () => {
  const feed = await getNotificationFeed();

  assert.deepEqual(
    feed.slice(0, 3).map((item) => item.notificationId),
    [804, 801, 802],
  );
});

test("draft queries expose filters, detail joins, and export audit visibility", async () => {
  const approvedDrafts = await getDraftList({
    status: "approved",
  });
  const detail = await getDraftDetail("101-bilibili");
  const exportRows = await getExportRecords();

  assert.deepEqual(
    approvedDrafts.map((draft) => draft.draftId),
    ["106-douyin", "101-xiaohongshu"],
  );
  assert.equal(detail?.draft.paper.paperId, 101);
  assert.ok(detail?.auditTrail.some((event) => event.label === "导出成功"));
  assert.equal(detail?.exportHistory[0]?.success, true);
  assert.equal(exportRows[0]?.draftTitle, "机器人视觉故障排查终于有索引了");
});
