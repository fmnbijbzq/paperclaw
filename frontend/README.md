# Paperclaw Frontend Companion

Standalone Next.js companion console for the Paperclaw backend. The app uses realistic demo data shaped around the backend domain entities in `app/models.py`, `app/editorial/pipeline.py`, `app/publish/exporter.py`, and `run_notify_once.py`.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Lucide React

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
- Demo data is in `frontend/lib/demo-data.ts`.
- Route structure:
  - `/`
  - `/papers`
  - `/papers/[paperId]`
  - `/pipeline`
  - `/notifications`
