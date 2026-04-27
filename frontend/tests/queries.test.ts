import assert from "node:assert/strict";
import test from "node:test";

import { getDashboardSnapshot, getPaperDetail, searchPapers } from "../lib/queries.ts";

test("getDashboardSnapshot derives overview metrics from demo data", () => {
  const snapshot = getDashboardSnapshot();

  assert.equal(snapshot.metrics.totalPapers.value, 6);
  assert.equal(snapshot.metrics.papersWithInsights.value, 4);
  assert.equal(snapshot.metrics.pendingNotifications.value, 2);
  assert.equal(snapshot.metrics.editorialDrafts.value, 6);
  assert.equal(snapshot.recentPapers[0]?.paper.paperId, 106);
});

test("searchPapers matches titles, authors, and categories", () => {
  const titleMatches = searchPapers("Gaussian");
  const authorMatches = searchPapers("Mei Chen");
  const categoryMatches = searchPapers("video");

  assert.equal(titleMatches.length, 1);
  assert.match(titleMatches[0]?.paper.title ?? "", /Gaussian/i);
  assert.equal(authorMatches[0]?.paper.paperId, 105);
  assert.equal(categoryMatches.length, 2);
});

test("getPaperDetail aggregates insight, notification, and editorial draft state", () => {
  const detail = getPaperDetail(101);

  assert.ok(detail);
  assert.equal(detail?.insight?.confidenceScore, 0.92);
  assert.equal(detail?.notifications.length, 1);
  assert.equal(detail?.editorialDrafts.length, 3);
  assert.equal(getPaperDetail(999), null);
});
