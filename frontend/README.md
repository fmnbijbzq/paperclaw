# Paperclaw Frontend

Next.js 15 dashboard for browsing papers, editorial drafts, pipeline status, and export records.

## Prerequisites

- **Node.js** >= 18
- **npm** (comes with Node.js)

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at **http://localhost:3000** by default.

## Available Scripts

| Command           | Purpose                                                       |
| ----------------- | ------------------------------------------------------------- |
| `npm run dev`     | Start the Next.js dev server with hot-reload                  |
| `npm run build`   | Create an optimised production build (output in `.next/`)     |
| `npm run start`   | Serve the production build (run `build` first)                |
| `npm run lint`    | Run ESLint with zero-warning policy                           |
| `npm run test`    | Run frontend unit tests                                       |
| `npm run clean`   | Delete the `.next` cache directory (see cache management)     |

### Development vs Production

```bash
# Development (hot-reload, source maps)
npm run dev

# Production (build once, then serve)
npm run build
npm run start          # serves on http://localhost:3000
```

## Environment Variables

The frontend reads its data source configuration from the browser at runtime.
By default it uses the **demo** data source (no backend required).

To connect to the live backend API, set either of the following environment
variables before building or running:

```bash
# .env.local (in the frontend/ directory)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Equivalent server-side configuration
PAPERCLAW_DATA_SOURCE=http
PAPERCLAW_API_BASE_URL=http://localhost:8000
```

When no API base URL is set the app falls back to demo data, so you can explore
the UI without the Python backend running.

## Cache Management (`.next` directory)

Next.js caches compiled pages and chunks in the `.next/` directory.  
Occasionally stale cache can cause build errors or unexpected behaviour.

### When to clean

- You pull new code and `npm run dev` shows stale pages
- `npm run build` fails with cryptic module-resolution errors
- You switch branches with significantly different page structures

### How to clean

```bash
# Using the provided script
npm run clean

# Or manually
rm -rf .next
```

Then restart the dev server or re-build:

```bash
npm run dev    # for development
npm run build  # for production
```

### Full clean start

If you want a completely fresh environment (including dependencies):

```bash
rm -rf node_modules .next
npm install
npm run dev
```

## Project Structure

```
frontend/
├── app/                  # Next.js App Router pages
│   ├── drafts/           # Editorial drafts list & detail
│   ├── exports/          # Export records
│   ├── papers/           # Paper browser
│   └── pipeline/         # Pipeline overview
├── components/           # Shared React components
├── lib/
│   ├── data-sources/     # Data adapters (http/, demo/)
│   ├── repositories/     # Data-access layer
│   ├── api-contracts.ts  # Shared API types & envelope helpers
│   └── types.ts          # Domain types
├── tests/                # Frontend unit tests
└── package.json
```

## Troubleshooting

| Problem                            | Fix                                            |
| ---------------------------------- | ---------------------------------------------- |
| Port 3000 already in use           | `npx next dev -p 3001` (or any free port)      |
| Stale pages after pulling code     | `npm run clean && npm run dev`                 |
| Build fails after branch switch    | `rm -rf node_modules .next && npm install`     |
| "Module not found" in dev mode     | Restart the dev server; if persistent, clean   |
