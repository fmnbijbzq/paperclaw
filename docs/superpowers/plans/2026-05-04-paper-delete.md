# Paper Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a destructive "delete paper" action to the dashboard's paper detail page that calls a new `DELETE /papers/{id}` endpoint, propagates the SQLAlchemy ORM cascade through related tables, and redirects back to the paper list on success.

**Architecture:** Backend adds one storage method (`Database.delete_paper`) that issues `session.delete(paper)` (ORM cascade fires for versions/insights/drafts/notifications, and through drafts → export_records/destination_records) plus an explicit `DELETE FROM paper_fetch_failures` (no FK, no ORM relationship). One new route `DELETE /papers/{paper_id}` gates on `require_api_key`. Frontend adds a `"use client"` component `PaperDeleteAction` (mirrors the existing `pipeline-task-control.tsx` direct-fetch pattern, no changes to `data-sources/`), threaded into the existing `paper-detail-hero.tsx` via a server-component-resolved `apiBaseUrl` / `apiKey` / `dataSource` prop trio.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2 / pytest / httpx · TypeScript / Next.js 15 App Router / React / lucide-react · `node:test` for contract assertions.

**Spec:** [`docs/superpowers/specs/2026-05-04-paper-delete-design.md`](../specs/2026-05-04-paper-delete-design.md)

---

## File Structure

```
app/storage.py                                 modify  # +PaperDeleteResult, +Database.delete_paper
app/api/schemas.py                             modify  # +PaperDeleteResponse
app/api/routes/papers.py                       modify  # +DELETE /papers/{paper_id}
tests/test_storage.py                          modify  # +1 unit test
tests/test_api_papers.py                       modify  # +4 route tests

frontend/lib/types.ts                          modify  # +PaperDeleteResult
frontend/lib/api-contracts.ts                  modify  # +PaperDeleteResponse
frontend/components/paper-delete-action.tsx    create  # client component, state machine, fetch
frontend/components/paper-detail-hero.tsx      modify  # +props, render <PaperDeleteAction>
frontend/app/papers/[paperId]/page.tsx         modify  # resolveRuntimeConfig, thread props
frontend/tests/api-contracts.test.ts           modify  # +1 contract test
```

---

## Task 1: Storage layer — `Database.delete_paper`

**Files:**
- Modify: `app/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1.1: Write the failing storage test**

Append to `tests/test_storage.py`:

```python
def test_delete_paper_returns_none_for_missing_id(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    assert db.delete_paper(999) is None


def test_delete_paper_wipes_paper_and_every_related_row(tmp_path):
    """Cascade contract: deleting a paper removes its versions, insights,
    drafts (and their export/destination records), notifications, AND any
    paper_fetch_failures matching (source, source_paper_id). The latter has
    no FK, so storage.delete_paper must clean it up explicitly."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    paper = db.upsert_paper(_build_paper("2404.01812", "Sparse Field Priors"))
    db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="x",
            summary_long="y",
            novelty_points=["n"],
            limitations=["l"],
            applications=["a"],
            confidence_score=0.5,
        ),
    )
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="t",
        hook="h",
        markdown_content="# t\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "fixture.md"),
    )
    db.record_notification_attempt(destination="feishu", paper=paper, success=True)
    # The draft state machine forces generated → in_review → approved → exported.
    # We need to walk it before record_export_success will accept the call.
    db.review_editorial_draft(draft.draft_id, actor="reviewer")
    db.approve_editorial_draft(draft.draft_id, actor="reviewer")
    db.record_export_success(
        draft_id=draft.draft_id,
        exported_by="tester",
        source_path=str(tmp_path / "outputs" / "editorial" / "fixture.md"),
        destination_path=str(tmp_path / "outputs" / "exported" / "fixture.md"),
    )
    db.create_destination_record(draft_id=draft.draft_id, platform="bilibili")

    # Seed a fetch_failure on the SAME (source, source_paper_id) — there's no
    # FK or relationship, so this is the row delete_paper must wipe explicitly.
    record = _build_paper("2404.01812", "Sparse Field Priors")
    db.record_paper_failure(
        source="arxiv",
        record=record,
        error_phase="upsert",
        error=RuntimeError("simulated"),
    )

    result = db.delete_paper(paper.paper_id)

    assert result is not None
    assert result.paper_id == paper.paper_id
    assert result.cascade_counts == {
        "versions": 1,           # upsert_paper inserted one PaperVersion
        "insights": 1,
        "drafts": 1,
        "notifications": 1,
        "exportRecords": 1,
        "destinationRecords": 1,
        "fetchFailures": 1,
    }

    # Verify nothing remains in the related tables. Since this test only
    # created one paper, every table being empty is a sufficient assertion.
    con = sqlite3.connect(f"{tmp_path/'papers.db'}")
    try:
        for table in (
            "papers", "paper_versions", "paper_insights",
            "editorial_drafts", "notifications", "export_records",
            "destination_records",
        ):
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0, f"expected {table} to be empty, got {count} rows"
        ff_count = con.execute(
            "SELECT COUNT(*) FROM paper_fetch_failures "
            "WHERE source = ? AND source_paper_id = ?",
            ("arxiv", "2404.01812"),
        ).fetchone()[0]
        assert ff_count == 0
    finally:
        con.close()
```

- [ ] **Step 1.2: Run the test to verify it fails**

```bash
make test ARGS="tests/test_storage.py::test_delete_paper_returns_none_for_missing_id tests/test_storage.py::test_delete_paper_wipes_paper_and_every_related_row -v"
```

Or, equivalently (if `make test` doesn't accept ARGS):

```bash
conda run -n paperclaw uv run pytest tests/test_storage.py::test_delete_paper_returns_none_for_missing_id tests/test_storage.py::test_delete_paper_wipes_paper_and_every_related_row -v
```

Expected: FAIL with `AttributeError: 'Database' object has no attribute 'delete_paper'`.

- [ ] **Step 1.3: Implement `PaperDeleteResult` dataclass and `Database.delete_paper`**

Edit `app/storage.py`. Add the import for `delete` near the existing SQLAlchemy imports (already `from sqlalchemy import create_engine, func, inspect, select, text, update`). Change to:

```python
from sqlalchemy import create_engine, delete, func, inspect, select, text, update
```

After the existing `UpsertPaperResult` dataclass (line ~19), insert:

```python
@dataclass(frozen=True)
class PaperDeleteResult:
    paper_id: int
    cascade_counts: dict[str, int]
```

Inside the `Database` class, immediately after `upsert_paper_with_status` (so it sits next to the other paper-write helpers), add:

```python
    def delete_paper(self, paper_id: int) -> PaperDeleteResult | None:
        """Delete a paper and every row that depends on it.

        Cascade map (all happens in one transaction):

          paper_versions         ← ORM relationship, cascade="all, delete-orphan"
          paper_insights         ← ORM relationship
          editorial_drafts       ← ORM relationship
            export_records       ← ORM relationship on EditorialDraft
            destination_records  ← ORM relationship on EditorialDraft
          notifications          ← ORM relationship
          paper_fetch_failures   ← NO FK / NO relationship; wiped explicitly

        Returns None if the paper doesn't exist (route uses this for 404).
        """
        with self._session() as session:
            paper = session.get(Paper, paper_id)
            if paper is None:
                return None

            # Pre-count children before delete fires (counts go in the
            # response and are used by tests to verify what was wiped).
            versions = session.scalar(
                select(func.count())
                .select_from(PaperVersion)
                .where(PaperVersion.paper_id == paper_id)
            ) or 0
            insights = session.scalar(
                select(func.count())
                .select_from(PaperInsight)
                .where(PaperInsight.paper_id == paper_id)
            ) or 0
            drafts = session.scalar(
                select(func.count())
                .select_from(EditorialDraft)
                .where(EditorialDraft.paper_id == paper_id)
            ) or 0
            notifications = session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.paper_id == paper_id)
            ) or 0
            # export_records / destination_records FK to drafts, not papers,
            # so we count them via a join through editorial_drafts.
            export_records = session.scalar(
                select(func.count())
                .select_from(ExportRecord)
                .join(EditorialDraft, ExportRecord.draft_id == EditorialDraft.draft_id)
                .where(EditorialDraft.paper_id == paper_id)
            ) or 0
            destination_records = session.scalar(
                select(func.count())
                .select_from(DestinationRecord)
                .join(EditorialDraft, DestinationRecord.draft_id == EditorialDraft.draft_id)
                .where(EditorialDraft.paper_id == paper_id)
            ) or 0
            fetch_failures = session.scalar(
                select(func.count())
                .select_from(PaperFetchFailure)
                .where(
                    PaperFetchFailure.source == paper.source,
                    PaperFetchFailure.source_paper_id == paper.source_paper_id,
                )
            ) or 0

            # Capture (source, source_paper_id) before delete clears the
            # in-session paper instance.
            source = paper.source
            source_paper_id = paper.source_paper_id

            session.delete(paper)
            # Explicit cleanup for the un-related table.
            session.execute(
                delete(PaperFetchFailure).where(
                    PaperFetchFailure.source == source,
                    PaperFetchFailure.source_paper_id == source_paper_id,
                )
            )
            session.commit()

            return PaperDeleteResult(
                paper_id=paper_id,
                cascade_counts={
                    "versions": versions,
                    "insights": insights,
                    "drafts": drafts,
                    "notifications": notifications,
                    "exportRecords": export_records,
                    "destinationRecords": destination_records,
                    "fetchFailures": fetch_failures,
                },
            )
```

- [ ] **Step 1.4: Run the test again to verify it passes**

```bash
conda run -n paperclaw uv run pytest tests/test_storage.py::test_delete_paper_returns_none_for_missing_id tests/test_storage.py::test_delete_paper_wipes_paper_and_every_related_row -v
```

Expected: 2 passed.

- [ ] **Step 1.5: Run the full storage test file to confirm no regressions**

```bash
conda run -n paperclaw uv run pytest tests/test_storage.py -v
```

Expected: all green.

- [ ] **Step 1.6: Commit**

```bash
git add app/storage.py tests/test_storage.py
git commit -m "$(cat <<'EOF'
feat(storage): add Database.delete_paper with full cascade cleanup

session.delete(paper) cascades through the ORM relationships for
versions, insights, drafts (and their export/destination records),
and notifications. paper_fetch_failures has no FK / no relationship,
so we wipe matching (source, source_paper_id) rows explicitly in the
same transaction. Returns PaperDeleteResult(paper_id, cascade_counts)
or None if the paper doesn't exist; the route uses None for 404.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Response schema — `PaperDeleteResponse`

**Files:**
- Modify: `app/api/schemas.py`

This task has no separate test — the route tests in Task 3 exercise the schema end-to-end. Steps are intentionally minimal.

- [ ] **Step 2.1: Add the model**

Edit `app/api/schemas.py`. After the existing `PaperDetailResponse` definition (around line 119), insert:

```python
class PaperDeleteResponse(ApiModel):
    deleted_paper_id: int = Field(alias="deletedPaperId")
    cascade_counts: dict[str, int] = Field(alias="cascadeCounts")
```

(Style match: `ApiModel` already enables `populate_by_name=True`, and every other field uses `alias="camelCaseName"`. Same convention here.)

- [ ] **Step 2.2: Verify it imports cleanly**

```bash
conda run -n paperclaw python -c "from app.api.schemas import PaperDeleteResponse; print(PaperDeleteResponse(deletedPaperId=1, cascadeCounts={'versions': 0}).model_dump(by_alias=True))"
```

Expected: `{'deletedPaperId': 1, 'cascadeCounts': {'versions': 0}}`

- [ ] **Step 2.3: Commit**

```bash
git add app/api/schemas.py
git commit -m "$(cat <<'EOF'
feat(api): add PaperDeleteResponse schema

Standard ApiModel with deletedPaperId + cascadeCounts (dict[str, int]).
Used by the upcoming DELETE /papers/{paper_id} route.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Route — `DELETE /papers/{paper_id}` + tests

**Files:**
- Modify: `app/api/routes/papers.py`
- Modify: `tests/test_api_papers.py`

- [ ] **Step 3.1: Write the four failing route tests**

Append to `tests/test_api_papers.py`:

```python
def test_delete_paper_with_children_cascades_and_returns_counts(tmp_path):
    """Happy path: paper with insight + draft + notification + fetch_failure
    is wiped and the response envelope reports cascade counts."""
    from tests.api_client import TEST_API_KEY

    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    editorial_dir = tmp_path / "outputs" / "editorial"
    app = create_app(
        database_url=database_url,
        editorial_root=editorial_dir,
        start_task_runner=False,
        api_key=TEST_API_KEY,
    )
    client = ASGITestClient(app)  # default api_key=TEST_API_KEY

    db = Database(database_url)
    db.create_schema()
    paper = db.upsert_paper(_build_paper())
    db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="s",
            summary_long="l",
            novelty_points=["n"],
            limitations=["lim"],
            applications=["app"],
            confidence_score=0.5,
        ),
    )
    db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="t",
        hook="h",
        markdown_content="# t\n",
        output_path=str(editorial_dir / "fixture.md"),
    )
    db.record_notification_attempt(destination="feishu", paper=paper, success=False, error_message="boom")
    db.record_paper_failure(
        source="arxiv",
        record=_build_paper(),
        error_phase="upsert",
        error=RuntimeError("simulated"),
    )

    response = client.delete(f"/papers/{paper.paper_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["dataSource"] == "http"
    assert payload["data"]["deletedPaperId"] == paper.paper_id
    counts = payload["data"]["cascadeCounts"]
    assert counts["insights"] == 1
    assert counts["drafts"] == 1
    assert counts["notifications"] == 1
    assert counts["fetchFailures"] == 1
    # versions defaulted to 1 by upsert_paper (it inserts one version on create)
    assert counts["versions"] == 1

    # The paper is actually gone
    follow_up = client.get(f"/papers/{paper.paper_id}")
    assert follow_up.status_code == 404


def test_delete_paper_returns_404_for_missing_id(tmp_path):
    from tests.api_client import TEST_API_KEY

    app = create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
        api_key=TEST_API_KEY,
    )
    client = ASGITestClient(app)

    response = client.delete("/papers/999999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_paper_returns_401_without_token(tmp_path):
    from tests.api_client import TEST_API_KEY

    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    app = create_app(
        database_url=database_url,
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
        api_key=TEST_API_KEY,
    )
    client = ASGITestClient(app, api_key=None)  # no Bearer header

    db = Database(database_url)
    db.create_schema()
    paper = db.upsert_paper(_build_paper())

    response = client.delete(f"/papers/{paper.paper_id}")

    assert response.status_code == 401
    # Paper still exists
    db_check = Database(database_url)
    assert db_check.count_papers() == 1


def test_delete_paper_returns_503_when_api_key_not_configured(tmp_path):
    """Fail-closed: a server with no API_KEY rejects deletes with 503."""
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    app = create_app(
        database_url=database_url,
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
        api_key=None,
    )
    client = ASGITestClient(app, api_key=None)

    db = Database(database_url)
    db.create_schema()
    paper = db.upsert_paper(_build_paper())

    response = client.delete(f"/papers/{paper.paper_id}")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()
```

- [ ] **Step 3.2: Run the tests to verify they fail**

```bash
conda run -n paperclaw uv run pytest tests/test_api_papers.py -k "delete_paper" -v
```

Expected: 4 FAIL (likely 405 Method Not Allowed because the route doesn't exist yet, or 404 — either way, not 200/401/503/404 in the right slot).

- [ ] **Step 3.3: Implement the route**

Edit `app/api/routes/papers.py`. Update the imports — change

```python
from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import EditorialDraftsResponse, PaperDetailResponse, PaperInsightsResponse, PapersListResponse, create_envelope
from app.api.services.editorial_workflow import list_drafts
from app.api.services.read_models import get_paper_detail, list_paper_insights, list_papers
```

to

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.schemas import EditorialDraftsResponse, PaperDeleteResponse, PaperDetailResponse, PaperInsightsResponse, PapersListResponse, create_envelope
from app.api.security import require_api_key
from app.api.services.editorial_workflow import list_drafts
from app.api.services.read_models import get_paper_detail, list_paper_insights, list_papers
```

At the bottom of the file, after the existing `get_paper` route, append:

```python
@router.delete("/{paper_id}")
async def delete_paper(
    request: Request,
    paper_id: int,
    actor: str = Depends(require_api_key),
) -> dict:
    del actor  # validated by require_api_key; not logged at this layer.
    db = request.app.state.db
    result = db.delete_paper(paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="paper not found")
    return create_envelope(
        PaperDeleteResponse(
            deletedPaperId=result.paper_id,
            cascadeCounts=result.cascade_counts,
        )
    ).model_dump(by_alias=True)
```

- [ ] **Step 3.4: Run the route tests to verify they pass**

```bash
conda run -n paperclaw uv run pytest tests/test_api_papers.py -k "delete_paper" -v
```

Expected: 4 passed.

- [ ] **Step 3.5: Run the full backend test suite to confirm no regressions**

```bash
conda run -n paperclaw uv run pytest -q
```

Expected: all green. (If anything else broke, fix before continuing — don't proceed with a red bar.)

- [ ] **Step 3.6: Commit**

```bash
git add app/api/routes/papers.py tests/test_api_papers.py
git commit -m "$(cat <<'EOF'
feat(api): DELETE /papers/{paper_id} endpoint

Gated on require_api_key (fail-closed). Returns 200 with envelope
{ deletedPaperId, cascadeCounts } on success, 404 if the paper doesn't
exist, 401 if the Bearer token is missing/wrong, 503 if API_KEY isn't
configured server-side. Tests cover all four paths.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Frontend types + contract test

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api-contracts.ts`
- Modify: `frontend/tests/api-contracts.test.ts`

- [ ] **Step 4.1: Write the failing contract test**

Edit `frontend/tests/api-contracts.test.ts`. In the existing import block at the top, append `PaperDeleteResponse` to the type list:

```ts
import {
  API_SCHEMA_VERSION,
  createApiEnvelope,
  createApiMeta,
  type EditorialDraftDetailResponse,
  type EditorialDraftsResponse,
  type ExportActionResponse,
  type ExportRecordsResponse,
  type NotificationFeedResponse,
  type PaperDeleteResponse,         // ← NEW
  type PaperDetailResponse,
  type PapersListResponse,
  type PipelineTaskCreateRequest,
  type PipelineTasksResponse,
  type PipelineSummaryResponse,
} from "../lib/api-contracts.ts";
```

At the bottom of the file (after the last existing test), append:

```ts
test("paper delete response wraps deletedPaperId + cascadeCounts in the standard envelope", () => {
  const body: PaperDeleteResponse = {
    deletedPaperId: 42,
    cascadeCounts: {
      versions: 1,
      insights: 1,
      drafts: 2,
      notifications: 3,
      exportRecords: 0,
      destinationRecords: 0,
      fetchFailures: 1,
    },
  };
  const envelope = createApiEnvelope<PaperDeleteResponse>(body, { dataSource: "http" });

  assert.equal(envelope.meta.schemaVersion, API_SCHEMA_VERSION);
  assert.equal(envelope.meta.dataSource, "http");
  assert.equal(envelope.data.deletedPaperId, 42);
  assert.equal(envelope.data.cascadeCounts.drafts, 2);
  assert.equal(envelope.data.cascadeCounts.fetchFailures, 1);
});
```

- [ ] **Step 4.2: Run the test to verify it fails**

```bash
cd /root/workspace/paperclaw/frontend && npm run test
```

Expected: FAIL with `Module '"../lib/api-contracts.ts"' has no exported member 'PaperDeleteResponse'.`

- [ ] **Step 4.3: Implement the types**

Edit `frontend/lib/types.ts`. After the existing `PaperRecord` interface (around line 111), insert:

```ts
export interface PaperDeleteResult {
  deletedPaperId: number;
  cascadeCounts: Record<string, number>;
}
```

Edit `frontend/lib/api-contracts.ts`. After the existing `PaperDetailResponse` interface (around line 105), insert:

```ts
export interface PaperDeleteResponse {
  deletedPaperId: number;
  cascadeCounts: Record<string, number>;
}
```

- [ ] **Step 4.4: Run the test to verify it passes**

```bash
cd /root/workspace/paperclaw/frontend && npm run test
```

Expected: all green.

- [ ] **Step 4.5: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api-contracts.ts frontend/tests/api-contracts.test.ts
git commit -m "$(cat <<'EOF'
feat(frontend): types + contract test for PaperDeleteResponse

PaperDeleteResult in lib/types.ts (consumer-facing) plus
PaperDeleteResponse in lib/api-contracts.ts (envelope shape). One
contract test verifies the envelope round-trips dataSource and the
camelCase cascadeCounts dictionary.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Frontend client component — `paper-delete-action.tsx`

**Files:**
- Create: `frontend/components/paper-delete-action.tsx`

This component has no test (no UI testing framework in the project — manual smoke at the end). Steps are: write file, lint, commit.

- [ ] **Step 5.1: Create the file**

Write `frontend/components/paper-delete-action.tsx`:

```tsx
"use client";

import { Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ApiDataSource } from "@/lib/api-contracts";

interface PaperDeleteActionProps {
  paperId: number;
  paperTitle: string;
  draftCount: number;
  hasInsight: boolean;
  apiBaseUrl: string | null;
  apiKey: string | null;
  dataSource: ApiDataSource;
}

type Status = "idle" | "confirming" | "deleting" | "error";

const HTTP_ERROR_LABEL: Record<number, string> = {
  401: "未授权（API_KEY 不正确或未发送）",
  403: "未授权（API_KEY 不正确或未发送）",
  404: "未找到论文（可能已被删除）",
  503: "服务端未配置 API_KEY，无法删除",
};

function describeError(error: unknown): string {
  if (error instanceof Error) {
    // Errors raised below carry "HTTP <status>" so we can map nicely.
    const httpMatch = /^HTTP (\d{3})$/.exec(error.message);
    if (httpMatch) {
      const status = Number(httpMatch[1]);
      return HTTP_ERROR_LABEL[status] ?? `删除失败：HTTP ${status}`;
    }
    if (error.message === "demo") {
      return "演示模式不支持删除";
    }
    return "网络错误，请重试";
  }
  return "删除失败：未知错误";
}

export function PaperDeleteAction({
  paperId,
  paperTitle,
  draftCount,
  hasInsight,
  apiBaseUrl,
  apiKey,
  dataSource,
}: PaperDeleteActionProps) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const liveMode = dataSource === "http" && apiBaseUrl !== null;

  function handleClickDelete() {
    setErrorMessage(null);
    setStatus("confirming");
  }

  function handleCancel() {
    setStatus("idle");
    setErrorMessage(null);
  }

  function handleConfirm() {
    if (!liveMode) {
      setErrorMessage("演示模式不支持删除");
      setStatus("error");
      return;
    }
    setStatus("deleting");
    setErrorMessage(null);
    startTransition(async () => {
      try {
        const headers: Record<string, string> = { accept: "application/json" };
        if (apiKey) {
          headers.Authorization = `Bearer ${apiKey}`;
        }
        const url = `${apiBaseUrl!.replace(/\/+$/, "")}/papers/${paperId}`;
        const response = await fetch(url, { method: "DELETE", headers });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        // Success — navigate away and refresh the list cache.
        router.push("/papers");
        router.refresh();
      } catch (error) {
        setErrorMessage(describeError(error));
        setStatus("error");
      }
    });
  }

  if (status === "idle") {
    return (
      <button
        type="button"
        onClick={handleClickDelete}
        disabled={!liveMode}
        className="action-button border border-[rgba(251,113,133,0.32)] bg-[rgba(251,113,133,0.08)] text-[color:var(--accent-rose)] hover:bg-[rgba(251,113,133,0.14)] disabled:cursor-not-allowed disabled:opacity-60"
        title={liveMode ? "永久删除此论文及其关联数据" : "演示模式不支持删除"}
      >
        删除
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    );
  }

  // confirming / deleting / error all render the inline danger region;
  // disabled state of buttons varies.
  const isDeleting = status === "deleting" || isPending;
  const insightCount = hasInsight ? 1 : 0;
  return (
    <div className="rounded-[1.25rem] border border-[rgba(251,113,133,0.32)] bg-[rgba(251,113,133,0.08)] p-4 text-[color:var(--accent-rose)]">
      <p className="text-sm font-semibold">确认删除？</p>
      <p className="mt-1 text-sm text-[color:var(--text-primary)]">
        将永久删除「{paperTitle.length > 30 ? `${paperTitle.slice(0, 30)}…` : paperTitle}」及{" "}
        {insightCount} 个洞察、{draftCount} 个草稿。该操作不可撤销。
      </p>
      {status === "error" && errorMessage ? (
        <p className="mt-3 text-sm font-medium text-[color:var(--accent-rose)]">{errorMessage}</p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isDeleting}
          className="action-button action-button-secondary disabled:cursor-not-allowed disabled:opacity-60"
        >
          取消
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isDeleting}
          className="action-button bg-[color:var(--accent-rose)] text-[#1a0709] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isDeleting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              删除中…
            </>
          ) : (
            <>
              确认删除
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5.2: Lint check (zero-warning policy)**

```bash
cd /root/workspace/paperclaw/frontend && npx eslint components/paper-delete-action.tsx --max-warnings 0
```

Expected: no output (success). If warnings appear, fix them — typically unused imports or missing key props.

- [ ] **Step 5.3: TypeScript check**

```bash
cd /root/workspace/paperclaw/frontend && npx tsc --noEmit
```

Expected: no output (success).

- [ ] **Step 5.4: Commit**

```bash
git add frontend/components/paper-delete-action.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): PaperDeleteAction client component

Mirrors pipeline-task-control.tsx: a "use client" component that
takes apiBaseUrl/apiKey/dataSource as props and issues fetch directly,
no data-sources layer involved (write actions in this codebase are
client-side direct fetch by convention).

State machine: idle → confirming → deleting → done (route push) | error.
Demo mode (dataSource !== "http" or apiBaseUrl == null) renders a
disabled button with a tooltip — no request is ever sent.

Error mapping: 401/403 → "未授权"; 404 → "未找到论文"; 503 → "服务端
未配置 API_KEY"; other HTTP → "删除失败：HTTP <status>"; fetch throw
→ "网络错误，请重试".

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Wire `PaperDeleteAction` into `paper-detail-hero.tsx`

**Files:**
- Modify: `frontend/components/paper-detail-hero.tsx`

- [ ] **Step 6.1: Add props and render the action**

Edit `frontend/components/paper-detail-hero.tsx`. Update the imports — change

```tsx
import { ArrowUpRight, BellRing, BrainCircuit, FileText, FileUp, Microscope } from "lucide-react";

import { formatFullDate, formatSource } from "@/lib/format";
import type { PaperRecord } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
```

to

```tsx
import { ArrowUpRight, BellRing, BrainCircuit, FileText, FileUp, Microscope } from "lucide-react";

import type { ApiDataSource } from "@/lib/api-contracts";
import { formatFullDate, formatSource } from "@/lib/format";
import type { PaperRecord } from "@/lib/types";
import { PaperDeleteAction } from "@/components/paper-delete-action";
import { StatusBadge } from "@/components/status-badge";
```

Update the `PaperDetailHeroProps` interface — change

```tsx
interface PaperDetailHeroProps {
  record: PaperRecord;
}
```

to

```tsx
interface PaperDetailHeroProps {
  record: PaperRecord;
  apiBaseUrl: string | null;
  apiKey: string | null;
  dataSource: ApiDataSource;
}
```

Update the component signature — change

```tsx
export function PaperDetailHero({ record }: PaperDetailHeroProps) {
```

to

```tsx
export function PaperDetailHero({ record, apiBaseUrl, apiKey, dataSource }: PaperDetailHeroProps) {
```

Inside the right-side action column, after the "打开 PDF" `<a>` and the "编辑就绪度" preview block — i.e. as the **last** child of the `<div className="flex flex-col gap-3 xl:w-72">` — insert the action:

```tsx
          <PaperDeleteAction
            paperId={record.paper.paperId}
            paperTitle={record.paper.title}
            draftCount={record.editorialDrafts.length}
            hasInsight={record.insight !== null}
            apiBaseUrl={apiBaseUrl}
            apiKey={apiKey}
            dataSource={dataSource}
          />
```

- [ ] **Step 6.2: Lint + TypeScript check**

```bash
cd /root/workspace/paperclaw/frontend && npx eslint components/paper-detail-hero.tsx --max-warnings 0 && npx tsc --noEmit
```

Expected: no output. If `tsc` fails because `app/papers/[paperId]/page.tsx` doesn't yet pass the new props — that's expected, fix in Task 7.

- [ ] **Step 6.3: Commit**

```bash
git add frontend/components/paper-detail-hero.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): render PaperDeleteAction in PaperDetailHero

New required props on the hero (apiBaseUrl/apiKey/dataSource) so it
can pass them straight to PaperDeleteAction. The hero stays a server
component — the action is the only client island.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Wire props from `app/papers/[paperId]/page.tsx`

**Files:**
- Modify: `frontend/app/papers/[paperId]/page.tsx`

- [ ] **Step 7.1: Resolve runtime config and thread props**

Edit `frontend/app/papers/[paperId]/page.tsx`. At the top, after the existing `import { getPaperDetail } from "@/lib/queries";`, add:

```tsx
import { resolveRuntimeConfig } from "@/lib/runtime-config";
```

Inside `PaperDetailPage`, after the existing `const record = await getPaperDetail(parsedPaperId);` and the `if (!record) { ... }` early-return, add:

```tsx
  const runtimeConfig = resolveRuntimeConfig();
```

Then update the `<PaperDetailHero record={record} />` line to pass the new props:

```tsx
      <PaperDetailHero
        record={record}
        apiBaseUrl={runtimeConfig.apiBaseUrl}
        apiKey={runtimeConfig.apiKey}
        dataSource={runtimeConfig.dataSource}
      />
```

- [ ] **Step 7.2: Lint + TypeScript check**

```bash
cd /root/workspace/paperclaw/frontend && npx eslint app/papers/\[paperId\]/page.tsx --max-warnings 0 && npx tsc --noEmit
```

Expected: no output.

- [ ] **Step 7.3: Run frontend tests one more time as a sanity check**

```bash
cd /root/workspace/paperclaw/frontend && npm run test
```

Expected: all green.

- [ ] **Step 7.4: Commit**

```bash
git add frontend/app/papers/\[paperId\]/page.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): thread runtime config to PaperDetailHero

Server-side resolveRuntimeConfig() reads PAPERCLAW_*/NEXT_PUBLIC_*
env vars and passes apiBaseUrl/apiKey/dataSource down to the hero,
which forwards to the client-side PaperDeleteAction.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Manual smoke test

**Files:** none (verification only)

This task verifies the end-to-end flow with `make dev`. No code changes, no commit.

- [ ] **Step 8.1: Confirm `.env` has `API_KEY` set**

```bash
grep '^API_KEY=' /root/workspace/paperclaw/.env || echo 'NOTE: API_KEY missing — set it before testing'
```

If absent, add a strong random value to `.env` and the same value to `frontend/.env.local` as `PAPERCLAW_API_KEY` (or `NEXT_PUBLIC_API_KEY`). The frontend needs to send it as Bearer; without it the delete button will return 401.

```
# .env
API_KEY=test-delete-key-1234

# frontend/.env.local
PAPERCLAW_API_KEY=test-delete-key-1234
```

- [ ] **Step 8.2: Start the dev environment**

```bash
make dev
```

Wait for the "API ready" message and the printed URLs.

- [ ] **Step 8.3: Walk the happy path**

1. Browser → `http://localhost:<WEB_PORT>/papers/4` (paper_id 4 is the first real arxiv record per earlier inspection — adjust to any paper that's safe to delete).
2. Confirm the hero shows "删除" button on the right side.
3. Click "删除" → confirm region appears with the cascade preview ("将永久删除…").
4. Click "确认删除" → button shows spinner → page navigates to `/papers`.
5. Verify the deleted paper no longer appears in the list.
6. Verify in DB:

```bash
conda run -n paperclaw python -c "
import sqlite3
con = sqlite3.connect('data/papers.db')
print('papers:', con.execute('SELECT COUNT(*) FROM papers WHERE paper_id=4').fetchone()[0])
print('insights:', con.execute('SELECT COUNT(*) FROM paper_insights WHERE paper_id=4').fetchone()[0])
print('drafts:', con.execute('SELECT COUNT(*) FROM editorial_drafts WHERE paper_id=4').fetchone()[0])
print('notifications:', con.execute('SELECT COUNT(*) FROM notifications WHERE paper_id=4').fetchone()[0])
"
```

Expected: every line is `0`.

- [ ] **Step 8.4: Walk the failure paths**

1. **401 path:** in DevTools Network tab, modify the next DELETE to send a wrong Bearer token (or remove `PAPERCLAW_API_KEY` from `frontend/.env.local`, restart, retry). Confirm inline error reads "未授权（API_KEY 不正确或未发送）" and the paper is **not** deleted.
2. **404 path:** delete a paper, then try clicking 确认删除 again on the stale page (it still has the old `paperId`). Confirm error reads "未找到论文（可能已被删除）".
3. **503 path:** restart the API with `API_KEY=` empty in `.env`, retry the delete. Confirm error reads "服务端未配置 API_KEY，无法删除".
4. **Demo mode:** unset `NEXT_PUBLIC_API_BASE_URL` and `PAPERCLAW_DATA_SOURCE`, restart frontend. Confirm the 删除 button is **disabled** with tooltip "演示模式不支持删除".

- [ ] **Step 8.5: Restore environment**

After smoke testing, restore `.env` and `frontend/.env.local` to their working state. No commit needed.

---

## Self-Review Checklist (run after writing the plan, before handoff)

- ✅ **Spec coverage:** Every section of the spec maps to a task.
  - Backend storage → Task 1
  - Backend response schema → Task 2
  - Backend route → Task 3
  - Frontend types + contract → Task 4
  - Frontend client component (state machine, error mapping, demo mode) → Task 5
  - Frontend hero integration → Task 6
  - Frontend page wiring → Task 7
  - Failure-mode catalog → covered by Tasks 3 (server-side) and 5+8 (client-side)
  - Manual smoke → Task 8
- ✅ **Type consistency:** `PaperDeleteResult` (frontend types.ts) matches the route's response data shape (`deletedPaperId` / `cascadeCounts`). `PaperDeleteResponse` (api-contracts.ts) is the envelope-data shape used for round-trip tests. Both backend and frontend use camelCase keys (`deletedPaperId`, `cascadeCounts`, `versions`/`insights`/`drafts`/`notifications`/`exportRecords`/`destinationRecords`/`fetchFailures`).
- ✅ **No placeholders:** Every code block contains exact, runnable code. No "TBD", "TODO", or "implement later".
- ✅ **TDD where the codebase supports it:** Backend storage and route tasks write the failing test first. Frontend types task writes the contract test first. UI component (Task 5) is implement-and-manual-smoke (no UI test framework in the project — matches the spec's "manual smoke test" decision).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-paper-delete.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**
