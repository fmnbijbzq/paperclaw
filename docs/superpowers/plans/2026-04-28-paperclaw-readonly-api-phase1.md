# Paperclaw Read-Only API Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal read-only HTTP API to the Python backend so the existing frontend can begin switching from demo mode to real `http` mode for papers, notifications, and pipeline summary data.

**Architecture:** Introduce a small FastAPI service layer that sits beside the current cron-oriented backend without changing the fetch/notify pipeline. Reuse the existing SQLAlchemy models and `Database` query methods wherever possible, add a thin API-oriented read service for joined views, and return stable JSON envelopes matching the frontend contracts already defined in `frontend/lib/api-contracts.ts`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, pytest, httpx TestClient/ASGI transport, existing Paperclaw storage layer

---

## Scope

This phase should implement the smallest useful read-only API surface for the frontend’s current HTTP skeleton assumptions:

- `GET /papers`
- `GET /papers/insights`
- `GET /papers/editorial-drafts`
- `GET /notifications`
- `GET /pipeline/summary`

This phase should **not**:

- Add write endpoints
- Change the fetch / notify cron pipeline behavior
- Add auth
- Add publish / retry actions yet
- Require the frontend to change its repository interfaces

## Current backend constraints and observations

- The project currently has **no existing FastAPI/Flask app**.
- `pyproject.toml` does not yet include `fastapi` or `uvicorn`.
- `app/storage.py` already provides several useful reads:
  - `list_papers_with_insights(limit=...)`
  - `list_notifications(destination=...)`
  - `count_papers()`
  - `get_paper_insight(paper_id=...)`
- `app/models.py` contains the canonical ORM models needed for serialization.
- Editorial drafts are currently filesystem-backed under `outputs/editorial/YYYY-MM-DD/`, so the API will need a lightweight file discovery layer for draft listing.
- Source health / pipeline summary are not fully materialized in one read model yet, so phase 1 should synthesize a minimal summary using existing database and file state.

## File Structure

### Dependency / entrypoint
- Modify: `pyproject.toml`
- Create: `run_api.py`

### API app and schemas
- Create: `app/api/__init__.py`
- Create: `app/api/app.py`
- Create: `app/api/deps.py`
- Create: `app/api/schemas.py`
- Create: `app/api/routes/__init__.py`
- Create: `app/api/routes/papers.py`
- Create: `app/api/routes/notifications.py`
- Create: `app/api/routes/pipeline.py`

### Read service layer
- Create: `app/api/services/__init__.py`
- Create: `app/api/services/read_models.py`
- Create: `app/api/services/editorial_index.py`
- Modify: `app/storage.py` only if a small reusable query helper is needed

### Tests
- Create: `tests/test_api_papers.py`
- Create: `tests/test_api_notifications.py`
- Create: `tests/test_api_pipeline.py`

### Docs
- Modify: `README.md`

## API contract alignment

The backend JSON should align with the frontend expectations already present in:

- `frontend/lib/api-contracts.ts`

The API should return a common envelope shape:

```json
{
  "data": { ... },
  "meta": {
    "dataSource": "http",
    "generatedAt": "2026-04-28T00:00:00Z",
    "schemaVersion": "2026-04-27"
  }
}
```

### Required route shapes

#### `GET /papers`
Return:
- `items`: list of paper list records containing
  - `paper`
  - `insight` summary fragment or `null`
  - `notificationSummary`
  - `editorialDraftCount`
- `total`
- `appliedQuery`

Phase 1 can support optional `query` and optional `limit` if cheap, but exact filtering breadth can stay minimal as long as the route is contract-correct.

#### `GET /papers/insights`
Return:
- `items`: full `PaperInsight`-style records
- `total`

#### `GET /papers/editorial-drafts`
Return:
- `items`: filesystem-derived draft records
- `total`

#### `GET /notifications`
Return:
- `items`: list of `{ notification, paperTitle, source }`
- `total`
- `failedCount`
- `successfulCount`

#### `GET /pipeline/summary`
Return:
- `metrics`
- `stages`
- `sourceHealth`

## Implementation Steps

### Task 1: Add FastAPI app skeleton and shared response schema

**Files:**
- Modify: `pyproject.toml`
- Create: `run_api.py`
- Create: `app/api/app.py`
- Create: `app/api/schemas.py`
- Create: `app/api/routes/__init__.py`
- Test: `tests/test_api_papers.py`

- [ ] Add failing test that imports the ASGI app and requests a placeholder route.
- [ ] Run the test to verify it fails because the app does not exist yet.
- [ ] Add `fastapi` and `uvicorn` dependencies.
- [ ] Implement the API app factory and shared envelope/meta schema.
- [ ] Re-run the targeted test until it passes.

### Task 2: Implement paper and insight read endpoints

**Files:**
- Create: `app/api/routes/papers.py`
- Create: `app/api/services/read_models.py`
- Modify: `app/storage.py` only if a very small helper is needed
- Test: `tests/test_api_papers.py`

- [ ] Add failing tests for `GET /papers`, `GET /papers/insights`, and `GET /papers/editorial-drafts`.
- [ ] Implement joined read serialization from ORM + editorial file discovery.
- [ ] Keep route outputs aligned with frontend contract field names.
- [ ] Re-run targeted tests until green.

### Task 3: Implement notification and pipeline summary endpoints

**Files:**
- Create: `app/api/routes/notifications.py`
- Create: `app/api/routes/pipeline.py`
- Create: `app/api/services/editorial_index.py`
- Test: `tests/test_api_notifications.py`
- Test: `tests/test_api_pipeline.py`

- [ ] Add failing tests for `GET /notifications` and `GET /pipeline/summary`.
- [ ] Implement notification feed shaping and minimal pipeline/source-health synthesis.
- [ ] Re-run targeted tests until green.

### Task 4: Wire entrypoint, document usage, and verify

**Files:**
- Create: `run_api.py`
- Modify: `README.md`

- [ ] Add a simple API launch entrypoint.
- [ ] Document how to run the read-only API locally.
- [ ] Document that this API is phase-1 read-only and intended for the frontend’s `http` mode.
- [ ] Run the full relevant test suite and fix issues until clean.

## Testing notes

Prefer isolated API tests using a temporary SQLite database and fixture data. The tests should:

- create schema
- insert papers / insights / notifications directly or via existing storage helpers
- create temporary editorial markdown files where needed
- call the ASGI app via test client
- assert JSON shape and key values

## Verification Checklist

- FastAPI app exists and starts locally.
- `GET /papers` returns the expected envelope and item shape.
- `GET /papers/insights` returns full insight records.
- `GET /papers/editorial-drafts` returns filesystem-derived draft items.
- `GET /notifications` returns frontend-compatible notification feed items.
- `GET /pipeline/summary` returns frontend-compatible metrics/stages/source-health.
- API output field names match the frontend contracts.
- Existing cron-oriented backend behavior remains unchanged.
- Relevant tests pass.
- README includes API run instructions.
