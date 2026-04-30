import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const repoFiles = [
  "app/loading.tsx",
  "app/papers/loading.tsx",
  "app/papers/[paperId]/loading.tsx",
  "app/exports/loading.tsx",
  "app/notifications/loading.tsx",
  "app/drafts/loading.tsx",
  "app/drafts/[draftId]/loading.tsx",
  "app/pipeline/loading.tsx",
  "app/error.tsx",
  "components/draft-audit-trail.tsx",
  "components/draft-filter-form.tsx",
  "components/editorial-preview-card.tsx",
  "components/error-panel.tsx",
  "components/notification-table.tsx",
  "lib/queries.ts",
];

const englishFragments = [
  "Bootstrapping",
  "Paper inventory",
  "Updated",
  "Output path",
  "No audit events recorded",
  "Notification delivery attempts",
  "Delivered",
  "Failed",
  "No error recorded",
  "Filter by status",
  "All statuses",
  "Retry route",
  "Draft generated",
  "Export succeeded",
];

test("operator-facing frontend copy is localized to Chinese", () => {
  const combinedCopy = repoFiles.map((path) => readFileSync(path, "utf8")).join("\n");

  for (const fragment of englishFragments) {
    assert.equal(combinedCopy.includes(fragment), false, `Found untranslated copy: ${fragment}`);
  }
});
