# Paperclaw Frontend HTTP Data Source Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Route B frontend architecture so the current repository layer can switch between demo-backed and HTTP-backed data sources through a single configuration boundary, without changing the page layer.

**Architecture:** Keep the repository interfaces stable, add HTTP data source skeletons that speak the existing API contracts, and centralize data source selection behind a lightweight runtime config/resolver. The implementation should remain safe for the current standalone frontend by defaulting to demo data while making real API integration a drop-in follow-up.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, Tailwind CSS 4, node:test, Codex CLI, UI/UX Pro Max skill guidance

---

## Scope

This phase should:

1. Introduce HTTP data source skeletons for papers, notifications, and pipeline.
2. Add a central resolver/config layer that chooses between `demo` and `http` data sources.
3. Keep demo mode as the default so existing pages continue to work unchanged.
4. Add tests for the resolver and for HTTP parsing/adaptation logic using fixtures or mocked fetch-style inputs.
5. Document how future backend integration should wire in base URL and source selection.

This phase should **not**:

- Require a live backend to run
- Add Python backend endpoints
- Change the visual design direction
- Break the existing repository contracts or page-level query APIs

## File Structure

### Planning / docs
- Create: `docs/superpowers/plans/2026-04-27-paperclaw-frontend-http-datasource-phase3.md`
- Modify: `frontend/README.md`

### Config / resolver layer
- Create: `frontend/lib/runtime-config.ts`
- Create: `frontend/lib/data-sources/index.ts`
- Modify: `frontend/lib/repositories/papers.ts`
- Modify: `frontend/lib/repositories/notifications.ts`
- Modify: `frontend/lib/repositories/pipeline.ts`

### HTTP data sources
- Create: `frontend/lib/data-sources/http/shared.ts`
- Create: `frontend/lib/data-sources/http/papers.ts`
- Create: `frontend/lib/data-sources/http/notifications.ts`
- Create: `frontend/lib/data-sources/http/pipeline.ts`
- Modify: `frontend/lib/api-contracts.ts` as needed for parsing helpers

### Tests
- Create: `frontend/tests/runtime-config.test.ts`
- Create: `frontend/tests/http-data-sources.test.ts`
- Modify: `frontend/tests/repositories.test.ts` if repository construction changes

## Implementation Steps

### Task 1: Add runtime config and data-source resolver

**Files:**
- Create: `frontend/lib/runtime-config.ts`
- Create: `frontend/lib/data-sources/index.ts`
- Modify: `frontend/lib/repositories/papers.ts`
- Modify: `frontend/lib/repositories/notifications.ts`
- Modify: `frontend/lib/repositories/pipeline.ts`
- Test: `frontend/tests/runtime-config.test.ts`

- [ ] Define a typed runtime config for data source mode (`demo` vs `http`) and optional API base URL.
- [ ] Resolve data sources from one shared boundary instead of directly importing demo implementations in repositories.
- [ ] Keep repositories defaulting to demo mode when no config is provided.
- [ ] Add tests validating the resolver behavior and safe defaults.

### Task 2: Add HTTP data source skeletons

**Files:**
- Create: `frontend/lib/data-sources/http/shared.ts`
- Create: `frontend/lib/data-sources/http/papers.ts`
- Create: `frontend/lib/data-sources/http/notifications.ts`
- Create: `frontend/lib/data-sources/http/pipeline.ts`
- Modify: `frontend/lib/api-contracts.ts` as needed
- Test: `frontend/tests/http-data-sources.test.ts`

- [ ] Add reusable HTTP helpers for request URL building and envelope validation assumptions.
- [ ] Implement HTTP data source skeletons that map API contract responses into existing repository-facing types.
- [ ] Avoid real network dependence in tests by injecting fetch-like behavior or response fixtures.
- [ ] Keep the shape ready for live backend wiring without overbuilding auth/retry systems yet.

### Task 3: Update docs and verify

**Files:**
- Modify: `frontend/README.md`

- [ ] Document how to switch the frontend between demo and future HTTP mode.
- [ ] Explain the purpose of runtime config and the HTTP skeleton layer.
- [ ] Run tests, lint, and build until clean.

## Verification Checklist

- Repositories no longer hardwire demo data source imports as the only default path.
- HTTP data source skeletons exist for papers, notifications, and pipeline.
- A central runtime config/resolver exists and defaults safely to demo mode.
- Existing page behavior still works in demo mode.
- Tests cover resolver behavior and HTTP data mapping.
- `npm run lint` passes.
- `npm run build` passes.
- `npm test` passes.
