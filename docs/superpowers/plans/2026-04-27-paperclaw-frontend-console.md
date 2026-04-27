# Paperclaw Frontend Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone frontend companion app for Paperclaw that visualizes paper ingestion, insight generation, notification status, and editorial/export workflows in a polished dashboard UI.

**Architecture:** The frontend will live in a new `frontend/` workspace inside the existing repository, using Next.js App Router for page composition and a thin in-repo data adapter layer with mock/demo data shaped around Paperclaw’s existing SQLite/domain models. The UI will emphasize operations visibility: source coverage, paper discovery timeline, paper detail exploration, notification queues, and content pipeline artifacts. Design language follows a dark, data-dense research-console style generated with UI/UX Pro Max and implemented through Codex.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS 4, Lucide React, ESLint, npm

---

## Scope

This frontend project is a **companion console**, not a replacement for the current Python runtime. It should:

- Present the current Paperclaw product model clearly
- Use realistic mock/demo data based on existing Python models (`Paper`, `PaperInsight`, `Notification`, editorial outputs)
- Be ready to connect to future APIs without major UI rewrites
- Include a landing/dashboard experience plus focused operational views
- Use accessible, production-quality UI patterns

This implementation does **not** need to:

- Connect directly to SQLite from Next.js
- Implement user auth
- Ship full CRUD settings management
- Replace current Feishu sending or crawler execution logic

## File Structure

### New frontend workspace
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/.gitignore`
- Create: `frontend/README.md`

### App shell and global styles
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`

### Route structure
- Create: `frontend/app/papers/page.tsx`
- Create: `frontend/app/papers/[paperId]/page.tsx`
- Create: `frontend/app/pipeline/page.tsx`
- Create: `frontend/app/notifications/page.tsx`

### Shared UI and domain modules
- Create: `frontend/components/app-shell.tsx`
- Create: `frontend/components/sidebar-nav.tsx`
- Create: `frontend/components/topbar.tsx`
- Create: `frontend/components/metric-card.tsx`
- Create: `frontend/components/section-card.tsx`
- Create: `frontend/components/status-badge.tsx`
- Create: `frontend/components/paper-list.tsx`
- Create: `frontend/components/paper-detail-hero.tsx`
- Create: `frontend/components/insight-panel.tsx`
- Create: `frontend/components/notification-table.tsx`
- Create: `frontend/components/pipeline-timeline.tsx`
- Create: `frontend/components/editorial-preview-card.tsx`
- Create: `frontend/components/source-health-card.tsx`
- Create: `frontend/components/empty-state.tsx`

### Data contracts and demo data
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/demo-data.ts`
- Create: `frontend/lib/queries.ts`

## Product / UX Definition

### Primary information architecture
1. **Overview (`/`)**
   - Mission header + system status
   - KPI strip: papers stored, papers with insights, pending notifications, editorial drafts
   - Source health cards for arXiv / OpenReview / CVF placeholder
   - Recent papers list
   - Content pipeline snapshot

2. **Papers (`/papers`)**
   - Search-style layout with summary cards
   - Highlight insight coverage, venue/source, confidence, categories
   - Dense research workflow feel rather than marketing gallery

3. **Paper Detail (`/papers/[paperId]`)**
   - Title, authors, source metadata, URLs
   - Short and long summary
   - Novelty / limitations / applications lists
   - Notification + editorial readiness side panels

4. **Pipeline (`/pipeline`)**
   - Visualize fetch → normalize → store → insight → editorial → export flow
   - Show generated draft artifacts by platform
   - Show what parts are already implemented in Paperclaw vs future-ready

5. **Notifications (`/notifications`)**
   - Delivery status list for Feishu records
   - Success/failure emphasis and queue explanation

### UI direction from research
- Dark professional “research operations console” aesthetic
- High-contrast data UI with cool blues and amber CTA accents
- Accessible text contrast and visible keyboard focus
- Lucide icons only, no emoji icons
- Fixed layout shell with sidebar + top status bar
- Dashboard cards with restrained glow and translucent dark panels

## Data Contract Mapping

The frontend demo models should mirror current Python code:

- `PaperItem`
  - maps to `Paper`
  - includes `paperId`, `title`, `abstract`, `authors`, `source`, `venue`, `categories`, `paperUrl`, `pdfUrl`, `publishedAt`
- `PaperInsightItem`
  - maps to `PaperInsight`
  - includes `summaryShort`, `summaryLong`, `noveltyPoints`, `limitations`, `applications`, `confidenceScore`
- `NotificationItem`
  - maps to `Notification`
  - includes `notificationId`, `destination`, `success`, `errorMessage`, `sentAt`, `paperId`
- `EditorialDraftItem`
  - derived from `outputs/editorial/*`
  - includes `platform`, `title`, `hook`, `status`, `updatedAt`
- `SourceHealthItem`
  - synthesized view for UI only
  - includes `source`, `enabled`, `status`, `lastRunAt`, `newCount`, `notes`

## Implementation Steps

### Task 1: Scaffold frontend workspace

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/.gitignore`
- Create: `frontend/README.md`

- [ ] Add a minimal Next.js + TypeScript + Tailwind workspace configuration.
- [ ] Add scripts for `dev`, `build`, `lint`.
- [ ] Document install/run commands in `frontend/README.md`.

### Task 2: Build app shell and theme

**Files:**
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/components/app-shell.tsx`
- Create: `frontend/components/sidebar-nav.tsx`
- Create: `frontend/components/topbar.tsx`
- Create: `frontend/components/section-card.tsx`
- Create: `frontend/components/status-badge.tsx`

- [ ] Implement root layout with font loading at layout level.
- [ ] Encode the dark “research console” design system in CSS variables.
- [ ] Add keyboard-visible focus styles and motion-safe transitions.
- [ ] Build persistent sidebar/topbar shell for all pages.

### Task 3: Add domain models and demo data

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/demo-data.ts`
- Create: `frontend/lib/queries.ts`

- [ ] Define TypeScript interfaces matching current backend domain objects.
- [ ] Seed realistic mock data based on Paperclaw’s existing source/insight/notification/editorial workflow.
- [ ] Add query helpers for overview metrics, paper lookup, notification list, and pipeline summaries.

### Task 4: Implement overview dashboard

**Files:**
- Create: `frontend/app/page.tsx`
- Create: `frontend/components/metric-card.tsx`
- Create: `frontend/components/source-health-card.tsx`
- Create: `frontend/components/pipeline-timeline.tsx`
- Create: `frontend/components/editorial-preview-card.tsx`

- [ ] Build hero/status area communicating what Paperclaw does.
- [ ] Add KPI metrics and source-health summary cards.
- [ ] Add pipeline visualization and editorial draft preview grid.
- [ ] Include a recent papers section linking into details.

### Task 5: Implement papers list and detail pages

**Files:**
- Create: `frontend/app/papers/page.tsx`
- Create: `frontend/app/papers/[paperId]/page.tsx`
- Create: `frontend/components/paper-list.tsx`
- Create: `frontend/components/paper-detail-hero.tsx`
- Create: `frontend/components/insight-panel.tsx`
- Create: `frontend/components/empty-state.tsx`

- [ ] Build list page with dense cards/rows suitable for research browsing.
- [ ] Build detail page showing title, metadata, summaries, novelty, limitations, and applications.
- [ ] Add empty/fallback state for unknown paper ids.

### Task 6: Implement pipeline and notifications views

**Files:**
- Create: `frontend/app/pipeline/page.tsx`
- Create: `frontend/app/notifications/page.tsx`
- Create: `frontend/components/notification-table.tsx`

- [ ] Build pipeline explainer page aligned with current Python scripts.
- [ ] Build notifications table emphasizing Feishu delivery reliability and retry logic.
- [ ] Show what is implemented now versus future extension points.

### Task 7: Verify and polish

**Files:**
- Modify: `frontend/**/*` as needed

- [ ] Run `npm install` in `frontend/`.
- [ ] Run `npm run lint`.
- [ ] Run `npm run build`.
- [ ] Fix any layout, typing, or build issues.
- [ ] Update `frontend/README.md` with exact usage notes.

## Verification Checklist

- Frontend builds successfully with `npm run build`
- Lint passes with `npm run lint`
- All routes render with no missing imports
- UI language accurately reflects current Paperclaw capabilities
- Demo data aligns with existing backend models and workflow
- Styling clearly reflects the requested UI Max-guided design work
