# Paperclaw Frontend Companion

Standalone Next.js companion console for the Paperclaw backend. The app uses realistic demo data shaped around the backend domain entities in `app/models.py`, `app/editorial/pipeline.py`, `app/publish/exporter.py`, and `run_notify_once.py`.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Lucide React

## Architecture

The frontend is still demo-data backed by default, but the app now routes data through an explicit contract, runtime config, and repository boundary so a future live backend can replace only the data-source layer.

- `frontend/lib/api-contracts.ts`
  Frontend-facing request/response contracts for future papers, paper detail, pipeline, and notifications endpoints.
- `frontend/lib/runtime-config.ts`
  Runtime mode resolution for `demo` vs `http`, plus the optional API base URL.
- `frontend/lib/data-sources/index.ts`
  Central resolver that selects demo or HTTP-backed data sources from the runtime config.
- `frontend/lib/data-sources/demo/*.ts`
  The active demo data source implementations. These read the current in-repo fixtures and expose async methods shaped like future HTTP-backed data sources.
- `frontend/lib/data-sources/http/*.ts`
  HTTP skeletons for papers, notifications, and pipeline data. These unwrap API envelopes and map them into the existing repository-facing shapes.
- `frontend/lib/repositories/*.ts`
  Domain repositories for papers, notifications, and pipeline data. They provide stable access patterns for sorting, lookups, and repository-level composition.
- `frontend/lib/queries.ts`
  Page-facing query composition. This is where repositories are joined into dashboard snapshots, paper records, and notification feeds for the route layer.
- `frontend/lib/demo-data.ts`
  Raw demo fixtures only. Route components and high-level queries should not depend on these arrays directly.

## Data flow

Current path:

`runtime-config.ts` -> `data-sources/index.ts` -> `data-sources/demo/*` -> `repositories/*` -> `queries.ts` -> `app/*`

Future live path:

`runtime-config.ts` -> `data-sources/index.ts` -> `data-sources/http/*` -> `repositories/*` -> `queries.ts` -> `app/*`

That keeps the page and component layer stable when the backend integration arrives.

## Runtime modes

The repository and query layers keep the page APIs unchanged while switching the underlying data source at one boundary.

- `demo`
  Default mode. No backend required. Repositories resolve the existing in-repo fixture-backed data sources.
- `http`
  Future backend mode. Repositories resolve lightweight HTTP data source skeletons that expect JSON API envelopes and map them back into the current repository-facing types.

Because the data access stays in the server-side repository layer, the mode is configured with server environment variables:

```bash
PAPERCLAW_DATA_SOURCE=demo
PAPERCLAW_API_BASE_URL=https://paperclaw.example/api
```

Behavior notes:

- If `PAPERCLAW_DATA_SOURCE` is unset or unsupported, the frontend safely falls back to `demo`.
- `PAPERCLAW_API_BASE_URL` is only required when `PAPERCLAW_DATA_SOURCE=http`.
- Tests do not require a live backend. The HTTP layer is exercised with injected fetch-style fixtures.

Current HTTP endpoint assumptions:

- `GET /papers`
- `GET /papers/insights`
- `GET /papers/editorial-drafts`
- `GET /notifications`
- `GET /pipeline/summary`

These are intentionally thin skeleton assumptions so live backend wiring can be added later without changing the route, query, or repository consumers.

## Install

```bash
cd frontend
npm install
```

## Run

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Build

```bash
cd frontend
npm run build
```

## Lint

```bash
cd frontend
npm run lint
```

## Notes

- The frontend is intentionally standalone and remains in `demo` mode by default.
- Demo data is still the active source of truth unless `PAPERCLAW_DATA_SOURCE=http` is explicitly configured.
- Route-level loading UI lives in `frontend/app/**/loading.tsx`.
- App-level recovery UI lives in `frontend/app/error.tsx` and `frontend/components/error-panel.tsx`.
- Route structure:
  - `/`
  - `/papers`
  - `/papers/[paperId]`
  - `/pipeline`
  - `/notifications`
