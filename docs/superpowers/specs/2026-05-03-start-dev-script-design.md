# Local Dev Startup Script — Design

**Date:** 2026-05-03
**Topic:** Provide a single command that starts both long-running surfaces (FastAPI backend + Next.js dashboard) for local development, with sensible pre-flight checks and a clean shutdown.

## Background

Paperclaw has four runnable surfaces (see `CLAUDE.md`):

1. `run_once.py` — one-shot crawl + summarize (cron daily)
2. `run_notify_once.py` — one-shot Feishu push (cron 10 min)
3. FastAPI server — `app.api.app:create_app` (long-running)
4. Next.js dashboard under `frontend/` (long-running)

Today, starting the dev environment requires running two commands in two terminals and remembering to set three env vars on the frontend (`NEXT_PUBLIC_API_BASE_URL`, `PAPERCLAW_API_BASE_URL`, `PAPERCLAW_DATA_SOURCE=http`) so the dashboard talks to the live backend instead of the bundled demo data.

This is a small but recurring friction point. We want one command (`make dev` or `./scripts/start-dev.sh`) that brings both up correctly.

## Goal

A developer can run `make dev` from a clean checkout and have:

1. The FastAPI server listening on `127.0.0.1:8000`.
2. The Next.js dashboard listening on `127.0.0.1:3000`, wired to the live backend.
3. Both processes' logs interleaved in one terminal with clear `[api]` / `[web]` prefixes, and also tee'd to `logs/dev-api.log` / `logs/dev-web.log`.
4. Ctrl+C cleanly stops both.
5. Common failure modes (port already taken, conda env missing, frontend deps not installed) surface as fail-fast errors before either process starts, not as cryptic mid-run crashes.

Cron-style one-shot scripts (`run_once.py`, `run_notify_once.py`) are out of scope — they already have `make run` / `make notify` and don't need a wrapper.

## Non-Goals

- Production deployment / process supervision (no systemd, pm2, docker-compose).
- `--api-only` / `--web-only` flags. If a developer wants to run one half under their IDE debugger, they can invoke the underlying commands directly (`uvicorn …` or `npm run dev`). YAGNI for now.
- Multi-worker uvicorn — `CLAUDE.md` explicitly warns the in-process `PipelineTaskRunner` is unsupported under `--workers 2+`. The dev script stays single-worker with `--reload`.

## Design

### File layout

```
scripts/start-dev.sh         # main logic, executable
Makefile                     # adds `dev` target that calls the script
```

The bash script holds all logic. The Makefile target is a thin shim so `make dev` works alongside the existing `make run` / `make notify` / `make smoke`. Keeping logic in bash (not the Makefile) avoids having to fight `make`'s rules around child processes, traps, and exit codes.

### Configuration

Environment variables, all optional:

| Var | Default | Purpose |
|-----|---------|---------|
| `API_PORT` | `8000` | uvicorn port |
| `WEB_PORT` | `3000` | Next.js dev server port |
| `API_HOST` | `127.0.0.1` | uvicorn bind host |
| `READY_TIMEOUT` | `30` | seconds to wait for backend readiness before giving up |

The script also auto-loads the project's `.env` (if present) before launching uvicorn, since `CLAUDE.md` documents many runtime variables (`DATABASE_URL`, `FEISHU_BOT_*`, `LOG_*`, `TIMEZONE`, …) that live there.

### Step-by-step behavior

1. **Locate project root** — `cd "$(dirname "$0")/.."` so the script works from any cwd.

2. **Pre-flight checks (fail fast):**
   - `conda env list` includes `paperclaw`. If not, print: *"conda env 'paperclaw' not found. Run `make env` first."* and exit 1.
   - `frontend/node_modules` exists. If not, run `npm install` in `frontend/` (this is a one-time cost on first checkout, not every start).
   - `lsof -iTCP:$API_PORT -sTCP:LISTEN` returns no rows; same for `$WEB_PORT`. If either is busy, print which port and which PID is holding it, then exit 1.
   - `mkdir -p logs/`.

3. **Load `.env`** — if `./.env` exists, `set -a; source ./.env; set +a` so its variables propagate to `uvicorn`.

4. **Start backend (background):**
   ```bash
   conda run --no-capture-output -n paperclaw \
     uvicorn app.api.app:create_app \
       --factory --reload \
       --host "$API_HOST" --port "$API_PORT" \
     > >(prefix '[api]' cyan | tee logs/dev-api.log) 2>&1 &
   API_PID=$!
   ```
   - `--no-capture-output` is required so logs stream live instead of buffering until exit.
   - **Process substitution (`> >(…)`) instead of a `cmd | prefix | tee &` pipeline** so that `$!` is the `conda run` (uvicorn) PID, not `tee`'s. With a plain pipeline, killing `$!` would only stop `tee` and leave uvicorn hanging on a SIGPIPE.

   `prefix` is a small shell function: it reads stdin line-by-line and prepends a colored tag if stdout is a tty, plain text otherwise. Color via ANSI escapes (`\033[36m` cyan, `\033[32m` green, `\033[0m` reset); tty detection via `[ -t 1 ]`.

5. **Wait for backend readiness:**
   ```bash
   for i in $(seq 1 "$READY_TIMEOUT"); do
       if curl -sf "http://$API_HOST:$API_PORT/openapi.json" >/dev/null; then
           break
       fi
       # also bail out if the api process died
       kill -0 "$API_PID" 2>/dev/null || { echo "[dev] api process exited"; exit 1; }
       sleep 1
   done
   curl -sf "http://$API_HOST:$API_PORT/openapi.json" >/dev/null \
       || { echo "[dev] api not ready after ${READY_TIMEOUT}s"; cleanup; exit 1; }
   ```
   `/openapi.json` is preferred over a `/health` endpoint because FastAPI publishes it automatically — no app-side change required.

6. **Start frontend (background):**
   ```bash
   ( cd frontend && \
     NEXT_PUBLIC_API_BASE_URL="http://localhost:$API_PORT" \
     PAPERCLAW_API_BASE_URL="http://localhost:$API_PORT" \
     PAPERCLAW_DATA_SOURCE=http \
     PORT="$WEB_PORT" \
     npm run dev \
   ) > >(prefix '[web]' green | tee logs/dev-web.log) 2>&1 &
   WEB_PID=$!
   ```
   Same process-substitution pattern as the backend so `$!` is the subshell wrapping `npm run dev`, killable with one TERM.

7. **Print access URLs (once both PIDs exist):**
   ```
   ──────────────────────────────────────────
    API   http://localhost:8000/docs
    Web   http://localhost:3000
   ──────────────────────────────────────────
   Press Ctrl+C to stop both.
   ```

8. **Wait + trap:**
   ```bash
   cleanup() {
       trap - INT TERM EXIT
       kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null || true
       wait "$API_PID" "$WEB_PID" 2>/dev/null || true
   }
   trap cleanup INT TERM EXIT
   wait
   ```

   Killing by PID is sufficient because uvicorn (run via `conda run --no-capture-output`) and `npm run dev` both forward signals to their children.

### Makefile addition

Append to `Makefile`:

```makefile
dev:
	./scripts/start-dev.sh
```

And add `dev` to the `.PHONY` list at the top of the file.

Place the target between `notify` and `smoke` to keep the rough "frequency of use" ordering already in the file.

## Failure-mode catalog

| Symptom | What user sees |
|---------|----------------|
| conda env missing | `conda env 'paperclaw' not found. Run \`make env\` first.` → exit 1, before anything starts |
| `frontend/node_modules` missing | Script runs `npm install` once and continues |
| Port 8000 busy | `port 8000 already in use (pid 12345 — node)` → exit 1 |
| Port 3000 busy | same shape | 
| API fails to start within 30s | API logs already streamed via `[api]` prefix; final line `[dev] api not ready after 30s`; backend killed; exit 1 |
| API crashes after starting, before frontend ready | `kill -0` check inside the readiness loop catches it: `[dev] api process exited` → exit 1 |
| User Ctrl+C | trap fires → `kill -TERM` both → `wait` → exit 0 |
| Frontend crashes mid-session | Backend keeps running (we only `wait`); user can Ctrl+C and restart. We don't auto-restart — that belongs to `next dev`'s own retry, not ours. |

## Testing

Manual smoke test only (this is a dev convenience script, not a deliverable):

1. Fresh checkout → `make env && make sync` → `make dev`. Both services come up; URLs printed; dashboard at `localhost:3000` shows live data (not demo).
2. Run `make dev` while another `make dev` is already running. Second invocation fails fast at the port check.
3. `make dev` then Ctrl+C. Both processes exit; `lsof -i:8000 -i:3000` is empty.
4. Temporarily break `app/api/app.py` (e.g., `raise RuntimeError` at module top). `make dev` should print the api stack trace under `[api]`, then time out and exit 1 within 30s — frontend never starts.
5. `make dev` with `API_PORT=9000 WEB_PORT=4000`. Both services bind to the overridden ports; URLs printed reflect them.

No automated tests — bash startup scripts are best validated by running them.

## Open questions

None. All decisions resolved during brainstorming:

- Format: bash script + `make dev` shim (not pure-Makefile).
- Logging: prefixed stdout + tee to `logs/`.
- Readiness: poll `/openapi.json` (no app-side changes needed).
- Single-mode: no `--api-only` / `--web-only`; YAGNI.
- `.env` auto-loaded for backend.
