# Paper Delete (Dashboard + API) — Design

**Date:** 2026-05-04
**Topic:** Add the ability to permanently delete a paper from the dashboard, with a corresponding write endpoint on the FastAPI backend.

## Background

Operators occasionally need to remove a paper from the database — for example, when a malformed `source_paper_id` was inserted (the original motivating case had `2404.0042`, a 4-digit arXiv ID that silently routes to an unrelated real paper at `2404.00042`), when seed/test data needs to be purged from a production-like DB, or when a paper was crawled but should be excluded from downstream pipelines.

Today the only path to remove a paper is direct SQL against `data/papers.db`, which is error-prone (the operator has to remember every cascade target) and inaccessible to non-engineers using the dashboard.

The codebase already has the surrounding infrastructure:

- **DB cascade is configured (mostly).** `Paper` has SQLAlchemy `relationship(..., cascade="all, delete-orphan")` to `PaperVersion`, `PaperInsight`, `EditorialDraft`, and `Notification`. `EditorialDraft` in turn cascades to `ExportRecord` and `DestinationRecord`. So `session.delete(paper)` cleans up six related tables at the ORM level (no SQLite `PRAGMA foreign_keys = ON` required). `PaperFetchFailure` is the **exception**: it has no FK to `papers` and no SQLAlchemy relationship — it tracks `(source, source_paper_id)` independently. We'll clean it up explicitly inside `delete_paper`.
- **Write-endpoint auth is solved.** `app/api/security.py::require_api_key` is fail-closed (HTTP 503 if the server has no `API_KEY` configured, HTTP 401 if the request lacks/has-wrong Bearer token). All existing mutations (draft approve / reject / assign / review / export) already use it.
- **The frontend already has a direct-fetch pattern for client-side mutations.** `frontend/components/pipeline-task-control.tsx` is the existing reference: a `"use client"` component that takes `apiBaseUrl: string | null`, `apiKey: string | null`, and `dataSource: ApiDataSource` as props from a server component (which gets them from `resolveRuntimeConfig()`), then issues `fetch(...)` directly with a Bearer header and `parseApiEnvelope` on the response. The `data-sources` layer is read-only in practice (its `post*` helpers are unused by any UI). We follow the `pipeline-task-control` pattern, not the data-sources one.

## Goal

A reviewer browsing `/papers/{paperId}` can:

1. Click a clearly destructive **删除** button in the hero card.
2. See an inline confirmation region listing exactly what will cascade (N versions, N insights, N drafts).
3. Confirm and observe the paper disappear: backend deletes the row + cascades, frontend redirects to `/papers`.
4. See a meaningful error message inline if the request fails (401 unauthorized, 503 server unconfigured, 5xx generic).

Deleting a paper through this flow is **functionally equivalent** to running:

```sql
DELETE FROM papers WHERE paper_id = N;
```

— with all FK cascade behavior the schema already specifies.

## Non-Goals

- **Soft delete / undo.** No `deleted_at` column, no archive view, no restore button. If recovery is needed, re-crawl from the source.
- **Batch delete on the list page.** Not on the list view at all — single-paper, detail-page-only entry point.
- **Disk-file cleanup.** `outputs/editorial/YYYY-MM-DD/<platform>/<slug>.md` files are NOT removed when their `editorial_drafts` row is cascaded away. Cleaning the editorial output tree belongs to a separate maintenance script (out of scope here).
- **Audit table.** `notifications` and `destination_records` cascade away with the paper. The user explicitly accepted this trade-off (CLAUDE.md describes notifications as append-only, but only within a paper's lifetime — once the paper is gone, its notification history goes with it).
- **Feishu notification on delete.** No outbound notification when a paper is deleted.
- **List-page changes** of any kind.

## Design

### End-to-end flow

```
[/papers/{id}] click "删除"
        ↓ (frontend state: idle → confirming)
hero shows inline danger region:
  "将永久删除此论文及 Y 个洞察、Z 个草稿。"
  (Y/Z come from existing PaperRecord fields — see "Cascade counts source" below.)
  [取消]  [确认删除]
        ↓ click 确认删除 (state: confirming → deleting)
DELETE /papers/{paperId}
  Authorization: Bearer <API_KEY>
        ↓
app.api.routes.papers.delete_paper
  → require_api_key dependency (401 / 503 fail-closed)
  → db.delete_paper(paper_id)
        ↓
storage.py::Database.delete_paper:
  1. SELECT counts of related rows (for response + log)
  2. session.delete(paper)             ← ORM cascade fires for versions /
                                         insights / drafts / notifications,
                                         and through drafts → export_records,
                                         destination_records
  3. session.execute(delete fetch_failures
        WHERE source = ? AND source_paper_id = ?)
  4. session.commit()
  5. return DeleteResult(paper_id, cascade_counts)
        ↓ HTTP 200
{ "data": { "deletedPaperId": N, "cascadeCounts": {...} }, "meta": {...} }
        ↓ (state: deleting → done)
frontend: router.push("/papers"); toast 已删除
```

### Backend

#### Storage layer (`app/storage.py`)

Add a single new method on the existing `Database` class:

```python
@dataclass(frozen=True)
class PaperDeleteResult:
    paper_id: int
    cascade_counts: Mapping[str, int]


class Database:
    ...

    def delete_paper(self, paper_id: int) -> PaperDeleteResult | None:
        """Delete a paper and every row that depends on it.

        Returns None if the paper does not exist.
        Returns PaperDeleteResult(paper_id, cascade_counts) on success.
        cascade_counts contains pre-deletion row counts for each related
        table — versions, insights, drafts, notifications, export_records,
        destination_records, fetch_failures — used by the API response
        and audit log.
        """
```

Implementation outline:

1. Open a session (use the existing `_session()` factory in this file).
2. `paper = session.get(Paper, paper_id)` — return None if missing.
3. Pre-compute child counts via `session.scalar(select(func.count()).where(...))` for each related table (including export_records and destination_records joined through drafts, and fetch_failures matched by `(source, source_paper_id)`). Done before delete so the counts reflect what was actually wiped.
4. `session.delete(paper)` — ORM cascade fires for `paper_versions`, `paper_insights`, `editorial_drafts` (and through drafts → `export_records`, `destination_records`), and `notifications`.
5. `session.execute(delete(PaperFetchFailure).where(source = paper.source, source_paper_id = paper.source_paper_id))` — explicit cleanup since this table has no FK / no relationship.
6. `session.commit()`.
7. Return `PaperDeleteResult`.

Cascade for the six related tables is via the **already-configured** SQLAlchemy `cascade="all, delete-orphan"` on the relationships in `app/models.py::Paper` and `app/models.py::EditorialDraft`. No schema changes. SQLite's `PRAGMA foreign_keys` is irrelevant because the cascade happens at the ORM layer (Python issues the child DELETEs explicitly), not at the SQL FK layer.

`paper_fetch_failures` is the only table that needs explicit cleanup: its `source_paper_id` column is plain `String(255)`, not a `ForeignKey`, and there's no `Paper.fetch_failures` relationship. Without step 5, deleting a paper would leave orphan rows that match the same `(source, source_paper_id)` and could confuse the retry path in `app/pipeline.py::_retry_pending_failures`.

#### Route (`app/api/routes/papers.py`)

```python
@router.delete("/{paper_id}")
async def delete_paper(
    request: Request,
    paper_id: int,
    actor: str = Depends(require_api_key),
) -> dict:
    db = request.app.state.db
    result = db.delete_paper(paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="paper not found")
    logger.info(
        "paper deleted",
        extra={"paper_id": paper_id, "actor": actor, "cascade": dict(result.cascade_counts)},
    )
    return create_envelope(
        PaperDeleteResponse(
            deletedPaperId=result.paper_id,
            cascadeCounts=dict(result.cascade_counts),
        )
    ).model_dump(by_alias=True)
```

`actor` follows the convention used in `drafts.py` (returned by `require_api_key` as `f"api:{token[:8]}"`); it's never sent to the client, only logged.

#### Schemas (`app/api/schemas.py`)

```python
class PaperDeleteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    deleted_paper_id: int
    cascade_counts: dict[str, int]
```

Standard envelope (`{ "data": ..., "meta": ... }`) via the existing `create_envelope` helper.

### Frontend

#### Type plumbing

Add to `frontend/lib/types.ts`:

```ts
export interface PaperDeleteResult {
  deletedPaperId: number;
  cascadeCounts: Record<string, number>;
}
```

Add a corresponding response type to `frontend/lib/api-contracts.ts` (no parser helper — the existing `parseApiEnvelope<T>` is enough):

```ts
export interface PaperDeleteResponse {
  deletedPaperId: number;
  cascadeCounts: Record<string, number>;
}
```

No changes to `lib/data-sources/`. Following the `pipeline-task-control.tsx` precedent, write actions live in the client component and call `fetch` directly — the data-sources layer is for SSR reads only.

#### New component: `components/paper-delete-action.tsx` (`"use client"`)

Mirrors the structure of `components/pipeline-task-control.tsx`. Props:

```ts
interface PaperDeleteActionProps {
  paperId: number;
  paperTitle: string;
  draftCount: number;
  hasInsight: boolean;
  apiBaseUrl: string | null;
  apiKey: string | null;
  dataSource: ApiDataSource;
}
```

State machine (local React state):

| State | UI |
|-------|-----|
| `idle` | Single danger-style button "删除" with `Trash2` icon. |
| `confirming` | Inline danger region appears below the button: heading "确认删除？"，副本 "将永久删除此论文及 Y 个洞察、Z 个草稿。该操作不可撤销。"，两个按钮 `[取消]` 和 `[确认删除]`。`Y/Z` come from `hasInsight ? 1 : 0` and `draftCount` props (no extra request). 版本数不展示（理由见下文 "Cascade counts source"）。 |
| `deleting` | `[确认删除]` 文案换成 `<Loader2 className="animate-spin" />` + "删除中…"；两个按钮都 disabled。 |
| `done` | `router.push("/papers")` 后整个 hero 已被替换，`done` 是瞬态。 |
| `error` | inline 区显示一条红色提示文字；按钮恢复可点（用户可重试或取消）。错误文案：401 → "未授权（API_KEY 不正确或未发送）"，503 → "服务端未配置 API_KEY，无法删除"，404 → "未找到论文（可能已被删除）"，其它 4xx/5xx → "删除失败：HTTP <status>"，fetch throws → "网络错误，请重试"。 |
| demo 模式 (`dataSource !== "http"` 或 `apiBaseUrl == null`) | 按钮始终 disabled + tooltip "演示模式不支持删除"。 |

Fetch logic (inline in this component, not in data sources):

```ts
async function performDelete(): Promise<void> {
  if (!apiBaseUrl) { /* shouldn't happen — button disabled */ return; }
  const headers: Record<string, string> = { accept: "application/json" };
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  const response = await fetch(
    `${apiBaseUrl.replace(/\/+$/, "")}/papers/${paperId}`,
    { method: "DELETE", headers },
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  // We don't need the response body — DELETE succeeded.
}
```

Use `useTransition()` for the deleting state (matches `pipeline-task-control.tsx` style). On success, `router.push("/papers")`.

#### `components/paper-detail-hero.tsx`

Stays a server component. Add the action to the right-side action column:

```
┌──────────────────────────────┐
│ 打开摘要页              ↗    │   primary
│ 打开 PDF                ⇪    │   secondary
│ <PaperDeleteAction … />      │   ← new
└──────────────────────────────┘
```

The hero gets new props: `apiBaseUrl`, `apiKey`, `dataSource`. It threads them straight into `<PaperDeleteAction>`.

#### `app/papers/[paperId]/page.tsx`

Server component. Add at the top, alongside `getPaperDetail`:

```ts
import { resolveRuntimeConfig } from "@/lib/runtime-config";

const runtimeConfig = resolveRuntimeConfig();
```

Then thread `runtimeConfig.apiBaseUrl`, `runtimeConfig.apiKey`, `runtimeConfig.dataSource` into `<PaperDetailHero record={record} apiBaseUrl={...} apiKey={...} dataSource={...} />`.

#### Cascade counts source

The existing `PaperRecord` already carries `editorialDrafts: DraftItem[]` and `insight: InsightItem | null`. For drafts and insights this gives accurate counts directly. For `versions` we currently don't ship version count to the frontend; rather than add it to the GET response just for this preview, **treat versions as "internal — not shown"** and display only `Y 个洞察、Z 个草稿` in the inline confirm region.

If a user expresses interest in seeing version count later, we can add it to `PaperDetailResponse` then. YAGNI for now.

## Failure-mode catalog

| Symptom | Where caught | What user sees |
|---------|--------------|----------------|
| `paper_id` does not exist | route → 404 | inline error: "未找到论文（可能已被删除）"，按钮恢复 |
| Server has no `API_KEY` configured | `require_api_key` → 503 | inline error: "服务端未配置 API_KEY，无法删除" |
| Request lacks Bearer token, or wrong token | `require_api_key` → 401 | inline error: "未授权（API_KEY 不正确或未发送）" |
| ORM cascade fails (DB-level error) | `delete_paper` → exception → 500 | inline error: "删除失败：HTTP 500"；session rolled back |
| Network error (fetch throws) | `paper-delete-action` → exception | inline error: "网络错误，请重试" |
| Demo mode (`dataSource !== "http"` 或 `apiBaseUrl == null`) | UI gate | 按钮 disabled + tooltip "演示模式不支持删除" — 不会发请求 |
| User clicks 取消 in `confirming` | UI only | 回到 `idle`，未发任何请求 |

## Testing

### Backend (`tests/test_api_papers.py`)

Add four tests, following existing fixture patterns (`_build_paper`, `db.upsert_paper`, `_make_client`, `ASGITestClient`):

1. **delete_paper_with_children_cascades** — insert a paper, attach an insight + a draft + a notification + a fetch_failure with the same `(source, source_paper_id)`, DELETE with valid token (default `ASGITestClient` Bearer), assert 200, envelope shape, `cascadeCounts` includes nonzero entries for `insights`, `drafts`, `notifications`, `fetchFailures`, and that subsequent SELECT on each related table returns 0 rows for that paper.
2. **delete_paper_404_when_missing** — DELETE on a paper_id that doesn't exist → 404.
3. **delete_paper_401_without_token** — `ASGITestClient(app, api_key=None)` against an app built with `api_key=TEST_API_KEY` → 401, and the paper is still in DB.
4. **delete_paper_503_when_api_key_not_configured** — build app with `api_key=None`, DELETE → 503.

Storage layer test in `tests/test_storage.py` adds one direct test: `delete_paper` returns `None` for missing IDs and the storage method itself returns the correct `cascade_counts`. The route tests above already cover the integration path, so the storage test focuses on the unit boundary.

### Frontend

Extend `frontend/tests/api-contracts.test.ts` with one case verifying the `PaperDeleteResponse` interface accepts the documented envelope shape (constructed via `createApiEnvelope`). No component-level tests for the inline confirm region — manual smoke test via `make dev`, documented at the end of the implementation plan.

## Open questions

None. All design decisions resolved during brainstorming:

- Hard delete; DB cascade only; no disk-file cleanup.
- Detail-page entry point only; no list-page changes.
- Inline confirm region in the hero (no modal component).
- API_KEY required (matches project convention).
- Versions count omitted from cascade preview (avoid adding a field just for one number).
