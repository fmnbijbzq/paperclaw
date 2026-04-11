# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paperclaw is a Python-based paper crawler that collects AI vision papers from multiple sources (arXiv, OpenReview), stores them in a SQLite database, and sends daily Feishu notifications.

**Core Principle:** "Grab all, store first, notify only new." The system is designed for idempotent execution with daily cron scheduling.

## Architecture

### Module Structure

```
runtime entrypoint          -> data normalization  -> database upsert
       ↓                                                                           ↓
app/sources/*.py           app/normalizer.py      app/storage.py
(BaseSource adapters)                                              ↓
                               ↓                                    ↓
                               └─────────────► app/pipeline.py ◄───┘
                                                               ↓
                                                        app/notifiers/
```

### Key Files

| File | Purpose |
|------|--------|
| `run_once.py` | Single-execution entry point for cron/manual runs |
| `app/pipeline.py` | Orchestrates fetch → normalize → upsert → notify flow |
| `app/storage.py` | Database operations via SQLAlchemy |
| `app/models.py` | SQLAlchemy ORM models (Paper, PaperVersion, CrawlRun, Notification) |
| `app/sources/base.py` | BaseSource abstract class for source adapters |
| `app/normalizer.py` | Builds dedup_key for cross-source duplicate detection |

### Source Adapters

Each source (`arxiv.py`, `openreview.py`, `cvf.py`) extends `BaseSource` and implements `fetch()` returning `list[PaperRecord]`. The base class provides `_get()` and `_post()` HTTP methods.

### Database Schema

- **papers**: Main table with `(source, source_paper_id)` unique constraint
- **paper_versions**: Version history for detecting paper metadata changes
- **crawl_runs**: Execution tracking per source per run
- **notifications**: Records which papers have been notified to avoid duplicates

### Deduplication Strategy

1. **Same-source dedup**: Guaranteed by `(source, source_paper_id)` unique constraint
2. **Cross-source dedup**: Soft matching via `dedup_key` (hashed title + first_author + year) — papers are NOT merged, just flagged as potential duplicates

### Notifier Design

The notifier receives a `PipelineSummary` with `new_papers` list. Notification failure does NOT roll back database operations — they are independently tracked.

## Common Commands

### Development Setup

```bash
python -m pip install -e .[dev]
```

### Run the Pipeline

```bash
python run_once.py
```

### Run All Tests

```bash
pytest tests/ -q
```

### Run Specific Test File

```bash
pytest tests/test_arxiv_source.py -q
```

### Run Live Feishu Integration Test

```bash
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' pytest -q -m integration
```

### Send Test Feishu Message

```bash
FEISHU_BOT_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxxx' python scripts/send_test_feishu_message.py
```

## Configuration

### Environment Variables (`.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite path, e.g., `sqlite:///data/papers.db` |
| `FEISHU_BOT_WEBHOOK` | Feishu webhook URL (optional) |
| `FEISHU_BOT_SECRET` | Secret for HMAC signature if enabled |
| `LOG_LEVEL` | Default: `INFO` |
| `TIMEZONE` | Default: `Asia/Shanghai` |
| `MAX_NOTIFY_ITEMS` | Max papers shown in notification, default: 10 |

### Source Configuration (`config/sources.yaml`)

```yaml
arxiv:
  enabled: true
  categories:
    - cs.CV
  lookback_days: 2

openreview:
  enabled: true
  venues:
    - CVPR
    - ICCV
    - ECCV
  lookback_days: 3
```

## Design Considerations

1. **PostgreSQL Migration Path**: The code avoids SQLite-specific features. Timezone-aware datetimes and JSON columns are used for compatibility.

2. **Error Isolation**: Each source run is tracked in a separate `CrawlRun` record. One source failing does not block others.

3. **Cron Deployment**: Example at `scripts/setup_cron.example`. Typical schedule: `0 8 * * *` (8 AM daily).

4. **Versioning**: When a paper's fields change, a `PaperVersion` snapshot is created. This enables future "paper update notifications."

5. **Feishu Signature Verification**: If `FEISHU_BOT_SECRET` is set, the notifier adds `timestamp` and `sign` fields per Feishu's requirements.

## Testing Conventions

- Fixture assertions must use `pytest` comparison functions, not `assertEqual` (imported from `unittest`)
- Use `httpx` transport fixtures for mocking HTTP calls in source tests
- Integration tests (real network calls to external services) are marked with `@pytest.mark.integration`

## Key Dependencies

- `sqlalchemy` - Database ORM
- `httpx` - HTTP client
- `pydantic`, `pydantic-settings` - Data validation and settings management
- `pyyaml` - Source configuration parsing
- `pytest` - Testing framework

## Architectural Decisions (from original spec)

- Uses SQLite first with PostgreSQL migration path
- Single-execution Python script orchestrated by cron (not a long-running service)
- Storage-success is independent of notification-success
- `dedup_key` is soft matching only — papers from different sources are NOT merged

