# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paperclaw is a Python paper crawler + content pipeline + dashboard for AI vision papers from arXiv, OpenReview, and CVF. It stores papers in a database, generates per-paper insights, composes platform-specific editorial drafts, and sends Feishu notifications. A Next.js dashboard fronts a FastAPI server for browsing and operating the system.

**Core principle:** "Grab all, store first, notify only new." The crawler is idempotent; storage success is independent of notification success.

## Architecture

The system has **four surfaces**, each able to run independently:

```
run_once.py              fetch -> normalize -> upsert -> summarize       (cron: daily)
run_notify_once.py       select unnotified -> send -> record             (cron: every 10m)
app.api.app:create_app   FastAPI server + in-process PipelineTaskRunner  (long-running)
frontend/                Next.js 15 dashboard                            (long-running)
```

`run_once.py` does **not** notify — that is the job of `run_notify_once.py`, which runs as a separate cron entry so failed sends can be retried in the next cycle. The FastAPI server hosts a thread-based `PipelineTaskRunner` that orchestrates crawl → editorial → notify stages on demand from the dashboard.

### Module layout

| Path | Role |
|------|------|
| `app/pipeline.py` | Crawl orchestration: fetch → normalize → upsert → summarize. Records a `CrawlRun` per source and a `SummarizationRun` per pipeline run. |
| `app/notification_pipeline.py` | Selects unnotified papers and sends one combined Feishu message per cycle. Each attempt is persisted in `notifications`. |
| `app/sources/{arxiv,openreview,cvf}.py` | Adapters extending `BaseSource`; each `fetch()` returns `list[PaperRecord]`. |
| `app/normalizer.py` | Builds `dedup_key` (hashed title + first_author + year) for cross-source soft matching. |
| `app/storage.py` | All database operations via SQLAlchemy. Single `Database` class. |
| `app/models.py` | ORM models — see schema below. |
| `app/summarization/service.py` | Generates `PaperInsight` (short/long summary, novelty, limitations, applications). |
| `app/enrichment/{chunker,extractor}.py` | PDF text chunking and content extraction used by summarization. |
| `app/editorial/{composer,pipeline}.py` | Renders Jinja2 templates (`templates/{bilibili,xiaohongshu,douyin}.md.j2`) into `outputs/editorial/YYYY-MM-DD/` and inserts `EditorialDraft` rows. |
| `app/publish/{base,bilibili,xiaohongshu,douyin,exporter}.py` | Per-platform publish adapters and the `outputs/exported/` exporter. |
| `app/notifiers/feishu_bot.py` | Feishu webhook client; HMAC signs when `FEISHU_BOT_SECRET` is set. |
| `app/tasks/pipeline_tasks.py` | `PipelineTaskRunner`: queue + worker thread that runs full crawl → editorial → notify against a single `PipelineTask` row. Started/stopped via the FastAPI lifespan. |
| `app/api/app.py` | `create_app(...)` factory. Wires DB, editorial root, and starts the task runner. |
| `app/api/routes/{papers,drafts,destinations,notifications,pipeline}.py` | REST endpoints; all responses use the `create_envelope(...)` shape. |
| `frontend/lib/data-sources/{http,demo}/` | Frontend swaps between live HTTP and demo data based on `NEXT_PUBLIC_API_BASE_URL` / `PAPERCLAW_DATA_SOURCE`. With no API URL, the dashboard runs entirely on demo data. |

### Database schema

Tables: `papers`, `paper_versions`, `paper_insights`, `editorial_drafts`, `export_records`, `destination_records`, `crawl_runs`, `summarization_runs`, `editorial_runs`, `pipeline_tasks`, `notifications`.

- `papers` has a `(source, source_paper_id)` unique constraint.
- `paper_versions` is appended whenever upsert detects field changes (enables future "paper updated" notifications).
- `paper_insights` is 1:1 with `papers` (`uq_paper_insights_paper_id`).
- `editorial_drafts` is 1:(paper_id, platform); each draft moves through statuses `generated → approved/rejected → exported`, with reviewer/approver fields.
- `pipeline_tasks` tracks dashboard-triggered runs with `current_stage` (`queued → crawl → editorial → notify → done | failed`) and `progress_current/progress_total`.
- `notifications` is append-only — a paper is "pending" if it has no `success=True` row for a given destination; failed sends remain retryable.

### Deduplication strategy

1. **Same source:** enforced by the `(source, source_paper_id)` unique constraint.
2. **Cross source:** soft via `dedup_key`. Papers from different sources are **never merged** — the key is only stored for future flagging/analytics.

### Editorial / publish flow

1. `run_once.py` (or a `pipeline_tasks` run) fills `papers` and `paper_insights`.
2. `scripts/run_content_pipeline.py --limit N` (or the task runner's editorial stage) renders drafts via `app/editorial/composer.py` into `outputs/editorial/YYYY-MM-DD/<platform>/<slug>.md` and inserts `EditorialDraft` rows.
3. Humans review/approve drafts (via dashboard or directly editing files).
4. `scripts/export_for_publish.py --date YYYY-MM-DD` copies approved drafts into `outputs/exported/YYYY-MM-DD/` and writes `export_records`.

## Common Commands

The Makefile assumes a conda env named `paperclaw` and uses `uv` underneath. Use `make` targets when available; raw equivalents are shown for non-conda setups.

### Setup

```bash
make env              # create conda env from environment.yml
make sync             # uv sync --extra dev (installs dev deps)

# Without conda:
uv sync --extra dev   # or: python -m pip install -e .[dev]
```

### Run

```bash
make run              # python run_once.py — crawl + summarize
make notify           # python run_notify_once.py — send pending notifications
make smoke            # scripts/send_test_feishu_message.py — webhook sanity check

# API server (dashboard backend):
conda run -n paperclaw uvicorn app.api.app:create_app --factory --reload

# Frontend dashboard:
cd frontend && npm install && npm run dev   # http://localhost:3000
```

The dashboard works without the API: leave `NEXT_PUBLIC_API_BASE_URL` unset and it uses demo data.

### Tests

```bash
make test                                                 # all tests via uv
pytest tests/ -q                                          # equivalent
pytest tests/test_pipeline.py -q                          # one file
pytest tests/test_api_pipeline.py -q                      # one API route's tests
pytest -q -m integration                                  # live network tests (skipped by default)

# Live Feishu integration:
FEISHU_BOT_WEBHOOK='https://...' pytest -q -m integration

# Frontend tests:
cd frontend && npm run test
```

## Configuration

### `.env`

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite path, e.g. `sqlite:///data/papers.db` |
| `FEISHU_BOT_WEBHOOK` | Feishu webhook URL (notifier disabled when empty) |
| `FEISHU_BOT_SECRET` | If set, notifier adds `timestamp` + HMAC `sign` to each request |
| `MAX_NOTIFY_ITEMS` | Cap on papers per combined Feishu message (default 10) |
| `PIPELINE_TASK_TIMEOUT_SECONDS` | Hard timeout for a dashboard-triggered pipeline task (default 1800). Worker checks between stages; exceeding the deadline finalizes the task as `failed` with `errorMessage="timeout after Ns"`. |
| `LOG_LEVEL`, `LOG_FORMAT`, `LOG_INCLUDE_LOCATION`, `LOG_FILE` | See `app/logging.py` |
| `TIMEZONE` | IANA tz, default `Asia/Shanghai` |

### `config/sources.yaml`

Three top-level keys: `arxiv`, `openreview`, `cvf`. Each has `enabled`, `lookback_days`, and source-specific knobs (`categories` / `venues` / `conferences`+`year`+`max_results`). Disabled sources are skipped at runtime; one source failing does not block others.

### Frontend env (`frontend/.env.local`)

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (and the equivalent server-side `PAPERCLAW_API_BASE_URL` + `PAPERCLAW_DATA_SOURCE=http`) to connect to the live backend. Without these, the dashboard uses bundled demo data.

## Design Considerations

1. **Two cron entries, not one.** `run_once.py` (8 AM daily) crawls and summarizes; `run_notify_once.py` (every 10 min) drains the unnotified queue. See `scripts/setup_cron.example`.
2. **PostgreSQL migration path.** No SQLite-specific features. Timezone-aware datetimes and JSON columns are used throughout `app/models.py`.
3. **Error isolation per source.** Each source gets its own `CrawlRun`. Source exceptions are caught in `app/pipeline.py` and the run continues.
4. **Notification independence.** A failed `notifier.send_combined(...)` never rolls back DB upserts; `notifications` rows record both successes and failures, and a paper stays pending until at least one `success=True` row exists.
5. **Pipeline task runner is in-process, single-worker only.** Started in the FastAPI lifespan as a daemon thread. The queue is in-memory but the runner **recovers from restarts**: on `start()` it (a) marks any `status='running'` task as `failed` with reason "orphaned by process restart" — its worker is gone — and (b) re-enqueues any `status='queued'` task. Each running row carries a `worker_id` and is acquired via an atomic `claim_pipeline_task` (UPDATE … WHERE status='queued'); a losing worker's `run_task_once` exits silently. Running uvicorn with `--workers 2+` is still **unsupported** because each process has its own in-memory queue.
6. **Cancellation is cooperative.** `cancel_pipeline_task` on a `queued` row transitions it directly to `cancelled` (terminal). On a `running` row it flips to `cancelling` (transient) — only the worker writes the final `cancelled` row + `finished_at`, observed at the next checkpoint between stages. Cancellation cannot interrupt an in-flight stage (e.g. a long PDF download); it only prevents the next stage from starting. The worker also checks an absolute deadline (`PIPELINE_TASK_TIMEOUT_SECONDS`) at each checkpoint and finalizes with `failed`+`"timeout after Ns"` if exceeded — this protects the single-worker queue from a stuck stage.

## Conventions

- Tests use plain `pytest` assertions — never `assertEqual` from `unittest`.
- Source-adapter tests use `httpx` `MockTransport` fixtures (see `tests/test_arxiv_source.py`).
- Live network tests are marked `@pytest.mark.integration` and excluded from default runs.
- API responses always go through `create_envelope(...)` from `app/api/schemas.py` — return shape is `{ "data": ..., "meta": ... }`.
- Editorial templates live in `app/editorial/templates/<platform>.md.j2` — add new platforms by adding a template + a publish adapter under `app/publish/`.

## Key Dependencies

- Backend: `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `pydantic`, `pydantic-settings`, `pyyaml`, `pypdf`, `jinja2`, `pytest`.
- Frontend: Next.js 15 (App Router), TypeScript, ESLint with zero-warning policy.
- Tooling: `uv` for dependency management, `conda` for the Python environment, `make` for orchestration.
