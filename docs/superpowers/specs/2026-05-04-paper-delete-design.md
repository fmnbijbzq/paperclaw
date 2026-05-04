# Paper Delete (Dashboard + API) — Design

**Date:** 2026-05-04
**Topic:** Add the ability to permanently delete a paper from the dashboard, with a corresponding write endpoint on the FastAPI backend.

## Background

Operators occasionally need to remove a paper from the database — for example, when a malformed `source_paper_id` was inserted (the original motivating case had `2404.0042`, a 4-digit arXiv ID that silently routes to an unrelated real paper at `2404.00042`), when seed/test data needs to be purged from a production-like DB, or when a paper was crawled but should be excluded from downstream pipelines.

Today the only path to remove a paper is direct SQL against `data/papers.db`, which is error-prone (the operator has to remember every cascade target) and inaccessible to non-engineers using the dashboard.

The codebase already has the surrounding infrastructure:

- **DB cascade is configured.** `paper_versions`, `paper_insights`, `editorial_drafts`, `notifications`, `destination_records`, and `paper_fetch_failures` all reference `papers.paper_id` with `ondelete="CASCADE"` and SQLAlchemy `cascade="all, delete-orphan"` on the parent relationship.
- **Write-endpoint auth is solved.** `app/api/security.py::require_api_key` is fail-closed (HTTP 503 if the server has no `API_KEY` configured, HTTP 401 if the request lacks/has-wrong Bearer token). All existing mutations (draft approve / reject / assign / review / export) already use it.
- **The frontend already has a Bearer-token HTTP client.** `frontend/lib/data-sources/http/shared.ts::createHttpClient` exposes `get` and `post`; adding `del` is a tiny mirror of `post`.

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
  2. session.delete(paper)
  3. session.commit()  ← FK ON DELETE CASCADE handles children
  4. return DeleteResult(paper_id, cascade_counts)
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
        """Delete a paper and all rows that FK-cascade off it.

        Returns None if the paper does not exist.
        Returns PaperDeleteResult(paper_id, cascade_counts) on success.
        cascade_counts contains pre-deletion row counts for each child table
        (versions, insights, drafts, notifications, destination_records,
        fetch_failures), used by the API response and audit log.
        """
```

Implementation outline:

1. Open a session (use the existing session factory pattern in this file).
2. `paper = session.get(Paper, paper_id)` — return None if missing.
3. Pre-compute child counts via `session.scalar(select(func.count()).where(...))` for each child table. Done before delete because cascade fires on commit and we want the counts in the response.
4. `session.delete(paper)`.
5. `session.commit()`.
6. Return the result.

The cascade itself relies on **already-configured** SQLAlchemy `cascade="all, delete-orphan"` plus the SQL FK `ondelete="CASCADE"`. No schema changes.

`paper_fetch_failures` cascades by FK only — there's no SQLAlchemy relationship from `Paper` to it (because failures live alongside `(source, source_paper_id)` rather than under a paper relationship). The SQL-level `ON DELETE CASCADE` still fires when the row is deleted, so this is correct without code changes.

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

Add to `frontend/lib/api-contracts.ts`:

```ts
export function parsePaperDeleteResponse(payload: unknown): PaperDeleteResult { ... }
```

Add `deletePaper(paperId: number): Promise<PaperDeleteResult>` to the `PapersDataSource` interface (`lib/data-sources/index.ts` or wherever the existing interface lives — follow the file conventions you find).

#### HTTP client (`http/shared.ts`)

Mirror the existing `post` method as `del`:

```ts
async del<TData>(path: string): Promise<TData> {
  const requestUrl = buildRequestUrl(options.baseUrl, path);
  const response = await fetchImplementation(requestUrl, {
    method: "DELETE",
    headers: buildAuthHeaders(apiKey, { accept: "application/json" }),
  });
  if (!response.ok) {
    throw new Error(`HTTP request failed with status ${response.status} for ${requestUrl}`);
  }
  return parseApiEnvelope<TData>(await response.json()).data;
},
```

#### Per-source implementations

- `http/papers.ts`: `deletePaper(paperId) => client.del<PaperDeleteResult>(\`papers/${paperId}\`)`
- `demo/papers.ts`: `deletePaper(_) => Promise.reject(new Error("delete not supported in demo data source"))`. Demo mode is read-only by design.

#### UI: `components/paper-detail-hero.tsx`

The hero already has an action column on the right (`打开摘要页`, `打开 PDF`). Add a third button below them styled as `danger`:

```
┌──────────────────────────────┐
│ 打开摘要页              ↗    │   primary
│ 打开 PDF                ⇪    │   secondary
│ 删除                    🗑    │   danger        ← new
└──────────────────────────────┘
```

State machine (local React state in the hero or its parent — see "Component split" below):

| State | UI |
|-------|-----|
| `idle` | 三个按钮可点。 |
| `confirming` | 在 hero 卡片底部展开一段红色 inline 区：标题 "确认删除？"，副本 "将永久删除此论文及 Y 个洞察、Z 个草稿。该操作不可撤销。"，两个按钮 `[取消]` 和 `[确认删除]`。`Y/Z` 来自现有 `record.insight`（0/1）和 `record.editorialDrafts.length`，不发任何额外请求。版本数不在前端 `PaperRecord` 上，故不展示（理由见下文 "Cascade counts source"）。 |
| `deleting` | `[确认删除]` 文案换成 spinner + "删除中…"；所有按钮（含取消、左侧链接）禁用。 |
| `done` | 路由跳到 `/papers` 并触发 toast "已删除：<paper.title 截短>"。 |
| `error` | 在 inline 区显示红色提示行；按钮恢复可点：401 → "未授权（API_KEY 不正确或未发送）"；503 → "服务端未配置 API_KEY"；其它 → 通用 "删除失败：<status>"。 |

#### Component split

The hero is currently a pure presentational component. The delete flow needs:

- Local state (`status`, `errorMessage`)
- Handler that calls the data source
- Router for redirect

Two options:

1. Keep `PaperDetailHero` presentational; lift state and handler to `app/papers/[paperId]/page.tsx`; pass `onDelete: () => Promise<void>`, `deleteState`, `deleteError` props down.
2. Make the hero a client component that owns the state, accept just `record` + a `useRouter` redirect inside.

**Recommendation: option 2.** The state is only meaningful inside the hero (no other component needs it), and `[paperId]/page.tsx` is currently a server component — keeping it that way is simpler than threading async state through. Add `"use client";` at the top of `paper-detail-hero.tsx`.

#### Cascade counts source

The existing `PaperRecord` already carries `editorialDrafts: DraftItem[]` and `insight: InsightItem | null`. For drafts and insights this gives accurate counts directly. For `versions` we currently don't ship version count to the frontend; rather than add it to the GET response just for this preview, **treat versions as "internal — not shown"** and display only `Y 个洞察、Z 个草稿` in the inline confirm region.

If a user expresses interest in seeing version count later, we can add it to `PaperDetailResponse` then. YAGNI for now.

## Failure-mode catalog

| Symptom | Where caught | What user sees |
|---------|--------------|----------------|
| `paper_id` does not exist | route → 404 | inline error: "未找到论文（可能已被删除）"，按钮恢复 |
| Server has no `API_KEY` configured | `require_api_key` → 503 | inline error: "服务端未配置 API_KEY，无法删除" |
| Request lacks Bearer token, or wrong token | `require_api_key` → 401 | inline error: "未授权（API_KEY 不正确或未发送）" |
| FK cascade fails (DB-level error) | `delete_paper` → exception → 500 | inline error: "删除失败：服务器错误"；DB rolled back |
| Network error (fetch throws) | data source → exception | inline error: "网络错误，请重试" |
| Demo mode (no backend) | `demo/papers.ts` rejects | inline error: "演示模式不支持删除" |
| User clicks 取消 in `confirming` | UI only | 回到 `idle`，未发任何请求 |

## Testing

### Backend (`tests/test_api_papers.py`)

Add four tests, following existing fixture patterns (`_build_paper`, `db.upsert_paper`, etc.):

1. **delete_paper_with_children_cascades** — insert a paper, attach an insight + a draft, DELETE with valid token, assert 200, envelope shape, cascade counts non-zero, and that subsequent SELECT on each child table returns 0 rows for that paper_id.
2. **delete_paper_404_when_missing** — DELETE on a paper_id that doesn't exist → 404.
3. **delete_paper_401_without_token** — DELETE with no Authorization header → 401, paper still in DB.
4. **delete_paper_503_when_api_key_not_configured** — create app with `api_key=None` → DELETE → 503.

Storage layer can have one direct test in `tests/test_storage.py` (or wherever the existing `Database` tests live) that verifies `delete_paper` returns `None` for missing IDs and that `cascade_counts` reflects the actual children — but the route tests above already cover the integration path, so this is optional.

### Frontend

Extend `frontend/tests/api-contracts.test.ts` with one case verifying `parsePaperDeleteResponse` accepts the documented envelope shape and rejects malformed input. No component-level tests for the inline confirm region — manual smoke test at `make dev`.

## Open questions

None. All design decisions resolved during brainstorming:

- Hard delete; DB cascade only; no disk-file cleanup.
- Detail-page entry point only; no list-page changes.
- Inline confirm region in the hero (no modal component).
- API_KEY required (matches project convention).
- Versions count omitted from cascade preview (avoid adding a field just for one number).
