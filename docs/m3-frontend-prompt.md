# Paperclaw M3 Frontend Implementation Plan

## Goal
Implement M3 (前端可运营) tasks T13-T16 for the Paperclaw frontend. This adds draft management, export management, and advanced paper search pages.

## Project Context
- **Framework**: Next.js 15 App Router, React, TypeScript
- **Design System**: Dark theme with `panel-card`, `eyebrow`, `section-title`, `subtle-copy` CSS classes
- **Data Pattern**: Repository → DataSource (demo/http) → API
- **Existing Pages**: Overview (`/`), Papers (`/papers`), Notifications (`/notifications`), Pipeline (`/pipeline`)
- **Components**: `SectionCard`, `EmptyState`, `PaperList`, `NotificationTable`, `MetricCard`, `StatusBadge`

## Backend API Endpoints (Already Implemented)

### Drafts API
```
GET  /api/drafts                    - List drafts (query params: status, platform, limit)
GET  /api/drafts/{draftId}          - Get draft detail with markdown content
POST /api/drafts/{draftId}/review   - Mark draft as reviewed
POST /api/drafts/{draftId}/approve  - Approve draft
POST /api/drafts/{draftId}/reject   - Reject draft  
POST /api/drafts/{draftId}/assign   - Assign draft to someone
POST /api/drafts/{draftId}/export   - Export draft
```

### Exports API
```
GET  /api/exports                   - List export records
```

### Papers API  
```
GET  /api/papers                    - List papers (query params: q, source, category, venue, hasInsight, hasDraft, page, pageSize)
GET  /api/papers/{paperId}          - Get paper detail
```

## Tasks

### T13: Draft List Page (`/drafts`)
Create `frontend/app/drafts/page.tsx` following the notifications page pattern.

**Requirements:**
- Show draft list with columns: title, platform, status, assignee, updatedAt
- Add status filter tabs (all/generated/in_review/approved/rejected/exported)
- Add platform filter (all/bilibili/xiaohongshu/douyin)
- Show summary stats at top (total drafts, pending review, approved, exported)
- Link each draft to `/drafts/{draftId}`

**Files to create/modify:**
- `frontend/app/drafts/page.tsx` - Main page
- `frontend/components/draft-table.tsx` - Draft list table component
- `frontend/lib/types.ts` - Add DraftStatus type
- `frontend/lib/queries.ts` - Add getDraftList function
- `frontend/lib/repositories/drafts.ts` - Draft repository
- `frontend/lib/data-sources/demo/drafts.ts` - Demo data source
- `frontend/lib/data-sources/http/drafts.ts` - HTTP data source
- `frontend/components/sidebar-nav.tsx` - Add drafts link

### T14: Draft Detail Page (`/drafts/[draftId]`)
Create `frontend/app/drafts/[draftId]/page.tsx` for draft review and approval.

**Requirements:**
- Show draft metadata (title, platform, status, assignee, timestamps)
- Render markdown content preview
- Action buttons: Review, Approve, Reject, Assign, Export
- Show associated paper info
- Status history/audit trail display

**Files to create:**
- `frontend/app/drafts/[draftId]/page.tsx` - Detail page
- `frontend/app/drafts/[draftId]/loading.tsx` - Loading state
- `frontend/components/draft-detail-hero.tsx` - Header component
- `frontend/components/draft-actions.tsx` - Action buttons
- `frontend/components/draft-preview.tsx` - Markdown preview

### T15: Export Management Page (`/exports`)
Create `frontend/app/exports/page.tsx` for viewing export history.

**Requirements:**
- List export records with: draft title, exportedBy, success/failure, timestamp
- Show error messages for failed exports
- Link back to source drafts
- Summary stats (total exports, success rate, recent failures)

**Files to create:**
- `frontend/app/exports/page.tsx` - Export list page
- `frontend/components/export-table.tsx` - Export records table
- `frontend/lib/repositories/exports.ts` - Export repository
- `frontend/lib/data-sources/demo/exports.ts` - Demo data source
- `frontend/lib/data-sources/http/exports.ts` - HTTP data source

### T16: Paper List Advanced Search
Update existing papers page to support backend search/filter/pagination.

**Requirements:**
- Add search input field (queries backend with `q` parameter)
- Add source filter dropdown (arxiv/openreview/cvf)
- Add category/venue filters
- Add hasInsight/hasDraft toggles
- Implement pagination (page/pageSize)
- Update repository to use HTTP data source when available

**Files to modify:**
- `frontend/app/papers/page.tsx` - Add search/filter UI
- `frontend/components/paper-search-bar.tsx` - Search component
- `frontend/components/paper-filters.tsx` - Filter controls
- `frontend/lib/repositories/papers.ts` - Add search/filter params
- `frontend/lib/data-sources/http/papers.ts` - Add query params
- `frontend/lib/queries.ts` - Update searchPapers function

## Implementation Notes

1. **Follow existing patterns**: Use the same component structure as notifications/papers pages
2. **Server Components**: Pages should be async server components
3. **Type Safety**: All API responses must match the schemas in `app/api/schemas.py`
4. **Demo Data**: Create realistic demo data for development without backend
5. **Error Handling**: Add proper loading states and error boundaries
6. **Responsive**: Follow existing responsive patterns (mobile-friendly)

## Verification
After implementation:
1. Run `cd frontend && npm run lint` - No lint errors
2. Run `cd frontend && npm run build` - Build succeeds
3. Run `cd frontend && npm run dev` - All pages load correctly
4. Test with demo data: All new pages show mock data
5. Test with HTTP backend: Pages fetch from API correctly
