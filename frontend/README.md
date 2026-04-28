# Paperclaw Frontend Companion

Standalone Next.js companion console for the Paperclaw backend. The app uses realistic demo data shaped around the backend domain entities in `app/models.py`, `app/editorial/pipeline.py`, `app/publish/exporter.py`, and `run_notify_once.py`.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Lucide React

## Architecture

The frontend is still demo-data backed, but the app now routes data through an explicit contract and repository boundary so a future live backend can replace only the data-source layer.

- `frontend/lib/api-contracts.ts`
  Frontend-facing request/response contracts for future papers, paper detail, pipeline, and notifications endpoints.
- `frontend/lib/data-sources/demo/*.ts`
  The active demo data source implementations. These read the current in-repo fixtures and expose async methods shaped like future HTTP-backed data sources.
- `frontend/lib/repositories/*.ts`
  Domain repositories for papers, notifications, and pipeline data. They provide stable access patterns for sorting, lookups, and repository-level composition.
- `frontend/lib/queries.ts`
  Page-facing query composition. This is where repositories are joined into dashboard snapshots, paper records, and notification feeds for the route layer.
- `frontend/lib/demo-data.ts`
  Raw demo fixtures only. Route components and high-level queries should not depend on these arrays directly.

## Data flow

Current path:

`demo-data.ts` -> `data-sources/demo/*` -> `repositories/*` -> `queries.ts` -> `app/*`

Future live path:

`backend HTTP API` -> `http data sources` -> `repositories/*` -> `queries.ts` -> `app/*`

That keeps the page and component layer stable when the backend integration arrives.

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

- The frontend is intentionally standalone and does not call the Python backend yet.
- Demo data is still the active source of truth, but it is now hidden behind async repositories and data sources.
- Route-level loading UI lives in `frontend/app/**/loading.tsx`.
- App-level recovery UI lives in `frontend/app/error.tsx` and `frontend/components/error-panel.tsx`.
- Route structure:
  - `/`
  - `/papers`
  - `/papers/[paperId]`
  - `/pipeline`
  - `/notifications`
