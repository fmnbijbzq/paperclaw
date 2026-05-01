# Editorial stage filter + CORS hardening — design

Date: 2026-05-01

Two scoped bug fixes against the dashboard-triggered pipeline and the API surface.

## Problem 1: editorial stage regenerates the same papers forever

`PipelineTaskRunner._run_editorial_stage` calls
`db.list_papers_with_insights(limit=editorial_limit)` which sorts by
`paper_id DESC` and returns the top N globally. Re-triggering the dashboard
task picks the same N "newest by id" papers on every run, so:

1. Newly crawled papers may never reach the editorial queue when older
   papers monopolise the limit window.
2. `db.upsert_editorial_draft(...)` overwrites existing rows and **resets**
   `status` back to `generated`, clearing `reviewed_by`, `approved_by`,
   `reviewed_at`, `approved_at`, and review notes — silently destroying
   human review work.

### Fix

- `app/storage.py`: extend `list_papers_with_insights` with
  `where_no_draft: bool = False`. When true, exclude any paper that
  already has *any* `EditorialDraft` row via
  `~Paper.paper_id.in_(select(EditorialDraft.paper_id))`.
- `app/tasks/pipeline_tasks.py`: `_run_editorial_stage` passes
  `where_no_draft=True`.
- CLI (`scripts/run_content_pipeline.py`) keeps default `False` so existing
  manual usage is unaffected.

This makes the dashboard editorial stage idempotent (re-runs do nothing
when there is no new work) and protects approval state.

`since=today` was rejected: it loses cross-day backfill and still
re-generates approved drafts within the same day.

## Problem 2: CORS `*` + `allow_credentials=True` trap

`AppSettings.cors_allow_origins` is a comma-separated string. If an
operator sets `CORS_ALLOW_ORIGINS=*`, `cors_allow_origins_list` returns
`["*"]`, which is fed to
`CORSMiddleware(allow_origins=["*"], allow_credentials=True)`. Browsers
forbid wildcard + credentials, so every cookie/Authorization-bearing
request fails with a CORS error and no obvious server-side signal.

### Fix

In `app/api/app.py::create_app`, after the resolved origin list is
computed, raise `ValueError` when `"*"` appears in it. Fail-fast on
startup with a clear message rather than silently shipping a broken
configuration. Cover both code paths (env-derived list and explicit
`cors_allow_origins=...` constructor argument).

`cors_allow_origins_list` stays a pure parser; the validation lives at
the wiring site.

## Test plan

New / changed tests:

- `tests/test_storage.py`
  - `list_papers_with_insights(where_no_draft=True)` excludes papers with
    any existing `EditorialDraft` row.
  - Default behaviour (`where_no_draft=False`) unchanged.
- `tests/test_pipeline_tasks.py`
  - Add a test that runs `_run_editorial_stage` twice against the same
    DB; the second call sees zero rows because the first inserted drafts.
- `tests/test_api_security.py` (or `tests/test_config.py`)
  - `create_app(cors_allow_origins=["*"])` raises `ValueError`.
  - Existing test paths that pass concrete origins keep passing.

All changes ship without DB migrations — `where_no_draft` is purely a
query-level filter.
