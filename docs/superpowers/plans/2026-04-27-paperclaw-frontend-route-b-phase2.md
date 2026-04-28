# Paperclaw Frontend Route B Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the Paperclaw frontend for future real backend integration by defining API contracts, abstracting data access behind repository/data-source layers, and adding loading/error/empty states without breaking the current polished console UI.

**Architecture:** Keep the current Next.js app visually intact while introducing an explicit domain contract and repository boundary. Demo data remains the active backend for now, but pages should depend on stable repository/query interfaces that could later swap to live HTTP implementations. Route-level loading and error handling should make the app feel product-ready before real APIs exist.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, Tailwind CSS 4, node:test, Codex CLI, UI/UX Pro Max skill guidance

---

## Scope

This phase should implement Route B from the optimization roadmap:

1. Define frontend-facing API contracts for papers, pipeline, and notifications.
2. Refactor the current demo data/query approach into repository + data source layers.
3. Add systematic loading / error / empty states to key pages.
4. Keep the current design system and visual direction stable.

This phase should **not**:

- Add real backend HTTP calls
- Change the Python backend
- Add auth or persistence from the frontend
- Replace the overall visual style already established

## File Structure

### Planning / docs
- Create: `docs/superpowers/plans/2026-04-27-paperclaw-frontend-route-b-phase2.md`
- Modify: `frontend/README.md`

### API contracts and repositories
- Create: `frontend/lib/api-contracts.ts`
- Create: `frontend/lib/repositories/papers.ts`
- Create: `frontend/lib/repositories/notifications.ts`
- Create: `frontend/lib/repositories/pipeline.ts`
- Create: `frontend/lib/data-sources/demo/papers.ts`
- Create: `frontend/lib/data-sources/demo/notifications.ts`
- Create: `frontend/lib/data-sources/demo/pipeline.ts`
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/queries.ts`
- Modify: `frontend/lib/demo-data.ts` as needed

### UI states
- Create: `frontend/app/loading.tsx`
- Create: `frontend/app/error.tsx`
- Create: `frontend/app/papers/loading.tsx`
- Create: `frontend/app/papers/[paperId]/loading.tsx`
- Create: `frontend/app/pipeline/loading.tsx`
- Create: `frontend/app/notifications/loading.tsx`
- Create: `frontend/components/loading-panel.tsx`
- Create: `frontend/components/error-panel.tsx`
- Modify: existing page files under `frontend/app/**/page.tsx` as needed

### Tests
- Modify: `frontend/tests/queries.test.ts`
- Create: `frontend/tests/repositories.test.ts`
- Create: `frontend/tests/api-contracts.test.ts`

## Implementation Steps

### Task 1: Define API contracts

**Files:**
- Create: `frontend/lib/api-contracts.ts`
- Modify: `frontend/lib/types.ts`
- Test: `frontend/tests/api-contracts.test.ts`

- [ ] Define TypeScript request/response contracts for future endpoints such as papers list, paper detail, pipeline summary, and notifications list.
- [ ] Keep the contracts aligned with existing domain types and current UI needs.
- [ ] Write tests validating the sample contract shapes and required fields through type-safe fixtures and runtime assertions where useful.

### Task 2: Introduce demo data sources and repository layer

**Files:**
- Create: `frontend/lib/repositories/papers.ts`
- Create: `frontend/lib/repositories/notifications.ts`
- Create: `frontend/lib/repositories/pipeline.ts`
- Create: `frontend/lib/data-sources/demo/papers.ts`
- Create: `frontend/lib/data-sources/demo/notifications.ts`
- Create: `frontend/lib/data-sources/demo/pipeline.ts`
- Modify: `frontend/lib/demo-data.ts`
- Modify: `frontend/lib/queries.ts`
- Test: `frontend/tests/repositories.test.ts`
- Test: `frontend/tests/queries.test.ts`

- [ ] Move page-facing data access away from direct demo-data reads into repository functions.
- [ ] Keep the repository API shaped so a future HTTP implementation can replace only the data-source layer.
- [ ] Preserve current behavior for dashboard, papers, paper detail, pipeline, and notifications.
- [ ] Add tests for repository outputs and core query derivations.

### Task 3: Add loading, error, and empty states

**Files:**
- Create: `frontend/app/loading.tsx`
- Create: `frontend/app/error.tsx`
- Create: `frontend/app/papers/loading.tsx`
- Create: `frontend/app/papers/[paperId]/loading.tsx`
- Create: `frontend/app/pipeline/loading.tsx`
- Create: `frontend/app/notifications/loading.tsx`
- Create: `frontend/components/loading-panel.tsx`
- Create: `frontend/components/error-panel.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/papers/page.tsx`
- Modify: `frontend/app/papers/[paperId]/page.tsx`
- Modify: `frontend/app/pipeline/page.tsx`
- Modify: `frontend/app/notifications/page.tsx`

- [ ] Add polished route-level loading screens matching the existing dark console style.
- [ ] Add a reusable error panel for recoverable UI messaging and the root error boundary.
- [ ] Ensure empty states remain explicit and visually consistent for no-results / no-record scenarios.
- [ ] Keep focus visibility, contrast, and layout density aligned with UI/UX Pro Max guidance.

### Task 4: Update docs and verify

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/package.json` only if new scripts are needed

- [ ] Document the new repository/data-source structure and future API integration path.
- [ ] Explain that demo data is still active but now hidden behind repositories and contracts.
- [ ] Run all relevant checks and fix issues until clean.

## Verification Checklist

- API contract types exist for future frontend/backend integration.
- Pages no longer depend directly on raw demo data structures where a repository boundary is more appropriate.
- Loading states exist for the root app and key routes.
- Error state exists at the app level and reusable component level.
- Empty states remain polished and useful.
- Existing console pages still render and preserve the design language.
- `npm run lint` passes.
- `npm run build` passes.
- Frontend tests pass.
