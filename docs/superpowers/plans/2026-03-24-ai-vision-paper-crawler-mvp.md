# AI Vision Paper Crawler MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MVP that fetches new AI vision papers from arXiv and OpenReview, stores them in SQLite with idempotent upserts, and sends daily Feishu bot notifications.

**Architecture:** The implementation uses a single-run CLI entrypoint (`run_once.py`) that orchestrates source adapters, normalization, deduplication, persistence, and notification. Source modules only fetch and map remote data, while storage and notification remain isolated behind focused interfaces so SQLite can later be replaced by PostgreSQL and Feishu bot notifications can later expand to Feishu Bitable sync.

**Tech Stack:** Python 3.12, `pytest`, `httpx`, `SQLAlchemy`, `pydantic`, `pydantic-settings`, `PyYAML`

---

## Preconditions

- The current workspace is not a Git repository yet. This plan includes a one-time `git init` step so later checkpoint commits work.
- Keep the MVP scope narrow:
  - Implement `arXiv` and `OpenReview`
  - Use `SQLite`
  - Send Feishu webhook notifications
  - Leave `CVF` as an interface placeholder only
- Use TDD for each module: write failing test, run it, implement minimum code, rerun test, then commit.

## File Structure

### Application files

- Create: `pyproject.toml`
  - Python package metadata and dependencies.
- Create: `.env.example`
  - Runtime environment variable template.
- Create: `config/sources.yaml`
  - Source toggles and lookback configuration.
- Create: `run_once.py`
  - Single-run CLI entrypoint for cron.
- Create: `app/__init__.py`
  - Package marker.
- Create: `app/config.py`
  - Load `.env` and `sources.yaml`.
- Create: `app/logging.py`
  - Configure structured logging.
- Create: `app/schemas.py`
  - `PaperRecord`, `SourceResult`, notification payload schemas.
- Create: `app/models.py`
  - SQLAlchemy metadata and table models.
- Create: `app/storage.py`
  - Database engine setup, schema creation, upsert/query helpers.
- Create: `app/normalizer.py`
  - Dedup key generation and source-to-record normalization helpers.
- Create: `app/pipeline.py`
  - End-to-end orchestration for one run.
- Create: `app/sources/__init__.py`
  - Source package marker.
- Create: `app/sources/base.py`
  - Source adapter protocol / abstract base.
- Create: `app/sources/arxiv.py`
  - arXiv adapter using Atom feed or API.
- Create: `app/sources/openreview.py`
  - OpenReview adapter using HTTP API.
- Create: `app/sources/cvf.py`
  - Placeholder adapter raising `NotImplementedError`.
- Create: `app/notifiers/__init__.py`
  - Notifier package marker.
- Create: `app/notifiers/feishu_bot.py`
  - Feishu webhook sender and card/text formatter.
- Create: `app/utils/__init__.py`
  - Utility package marker.
- Create: `app/utils/hashers.py`
  - Dedup key helpers.
- Create: `app/utils/time.py`
  - Timezone-aware time helpers.

### Test files

- Create: `tests/conftest.py`
  - Shared fixtures for temp DB path, fake config, and mocked HTTP.
- Create: `tests/test_config.py`
  - Config loading tests.
- Create: `tests/test_hashers.py`
  - Dedup key normalization tests.
- Create: `tests/test_storage.py`
  - Schema creation, insert, update, notification tests.
- Create: `tests/test_arxiv_source.py`
  - arXiv parsing tests.
- Create: `tests/test_openreview_source.py`
  - OpenReview parsing tests.
- Create: `tests/test_feishu_bot.py`
  - Notification formatting and HTTP submission tests.
- Create: `tests/test_pipeline.py`
  - End-to-end orchestration tests with fake sources.
- Create: `tests/test_run_once.py`
  - CLI smoke test.

### Docs and ops files

- Create: `README.md`
  - Setup, usage, and cron instructions.
- Create: `scripts/setup_cron.example`
  - Example cron line for deployment.

## Task 1: Bootstrap Project and Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_run_once.py`

- [ ] **Step 1: Initialize Git repository**

Run:

```bash
git init
```

Expected: `.git/` directory is created in `/root/workspace/paperclaw`.

- [ ] **Step 2: Write the failing CLI smoke test**

```python
from pathlib import Path


def test_project_root_contains_run_once_script():
    assert Path("run_once.py").exists()
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
pytest tests/test_run_once.py -q
```

Expected: FAIL because `run_once.py` does not exist yet.

- [ ] **Step 4: Create minimal project scaffolding**

```python
def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Also create `pyproject.toml` with:

- `python >=3.12`
- runtime deps: `httpx`, `sqlalchemy`, `pydantic`, `pydantic-settings`, `pyyaml`
- dev deps: `pytest`

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
pytest tests/test_run_once.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml run_once.py app/__init__.py tests/test_run_once.py
git commit -m "chore: bootstrap paper crawler project"
```

## Task 2: Add Configuration and Logging Foundations

**Files:**
- Create: `.env.example`
- Create: `config/sources.yaml`
- Create: `app/config.py`
- Create: `app/logging.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

```python
from app.config import AppSettings, load_source_config


def test_app_settings_reads_database_url():
    settings = AppSettings.model_validate(
        {
            "database_url": "sqlite:///data/papers.db",
            "feishu_bot_webhook": "https://example.invalid/hook",
        }
    )
    assert settings.database_url == "sqlite:///data/papers.db"


def test_load_source_config_reads_arxiv_categories(tmp_path):
    config_file = tmp_path / "sources.yaml"
    config_file.write_text("arxiv:\n  enabled: true\n  categories:\n    - cs.CV\n")
    data = load_source_config(config_file)
    assert data["arxiv"]["categories"] == ["cs.CV"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing symbols.

- [ ] **Step 3: Implement minimal settings and YAML loader**

```python
class AppSettings(BaseSettings):
    database_url: str
    feishu_bot_webhook: str | None = None
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"
    max_notify_items: int = 10
```

And add:

- `load_source_config(path: Path) -> dict`
- `.env.example`
- default `config/sources.yaml`
- `configure_logging()` helper

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .env.example config/sources.yaml app/config.py app/logging.py tests/test_config.py
git commit -m "feat: add configuration and logging setup"
```

## Task 3: Define Core Schemas and Hashing Helpers

**Files:**
- Create: `app/schemas.py`
- Create: `app/utils/hashers.py`
- Create: `app/utils/time.py`
- Create: `app/utils/__init__.py`
- Test: `tests/test_hashers.py`

- [ ] **Step 1: Write failing dedup tests**

```python
from app.utils.hashers import build_dedup_key, normalize_title


def test_normalize_title_strips_case_and_punctuation():
    assert normalize_title("Segment Anything: A Foundation Model!") == "segment anything a foundation model"


def test_build_dedup_key_is_stable_for_same_title():
    a = build_dedup_key("Segment Anything", first_author="Kirillov", year=2023)
    b = build_dedup_key("segment anything", first_author="Kirillov", year=2023)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_hashers.py -q
```

Expected: FAIL because helper functions are missing.

- [ ] **Step 3: Implement shared schemas and helpers**

Create:

- `PaperRecord`
- `SourceFetchResult`
- `NotificationSummary`
- `normalize_title()`
- `build_dedup_key()`
- timezone-aware `utc_now()` helper

Minimal schema example:

```python
class PaperRecord(BaseModel):
    source: str
    source_paper_id: str
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    paper_url: str
    pdf_url: str | None = None
    venue: str | None = None
    categories: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    updated_at_source: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_hashers.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py app/utils/__init__.py app/utils/hashers.py app/utils/time.py tests/test_hashers.py
git commit -m "feat: add shared schemas and dedup helpers"
```

## Task 4: Implement Database Models and Persistence Layer

**Files:**
- Create: `app/models.py`
- Create: `app/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing persistence tests**

```python
from app.schemas import PaperRecord
from app.storage import Database


def test_database_creates_tables(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    assert db.table_exists("papers")


def test_upsert_paper_is_idempotent(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    paper = PaperRecord(
        source="arxiv",
        source_paper_id="1234.5678",
        title="Test Paper",
        paper_url="https://arxiv.org/abs/1234.5678",
    )
    first = db.upsert_paper(paper)
    second = db.upsert_paper(paper)
    assert first.paper_id == second.paper_id
    assert db.count_papers() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_storage.py -q
```

Expected: FAIL because `Database` and schema are missing.

- [ ] **Step 3: Implement SQLAlchemy schema and repository**

Create tables:

- `papers`
- `paper_versions`
- `crawl_runs`
- `notifications`

Implement methods:

- `create_schema()`
- `table_exists(name)`
- `start_crawl_run(source)`
- `finish_crawl_run(...)`
- `upsert_paper(record)`
- `record_notification(...)`
- `list_unnotified_papers(...)`
- `count_papers()`

Use unique constraint on `(source, source_paper_id)`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_storage.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/storage.py tests/test_storage.py
git commit -m "feat: add database schema and persistence layer"
```

## Task 5: Implement arXiv Source Adapter

**Files:**
- Create: `app/sources/base.py`
- Create: `app/sources/arxiv.py`
- Create: `app/sources/__init__.py`
- Test: `tests/test_arxiv_source.py`

- [ ] **Step 1: Write failing arXiv parsing test**

```python
from app.sources.arxiv import ArxivSource


def test_arxiv_source_parses_atom_entry(httpx_mock):
    httpx_mock.add_response(
        text=\"\"\"<?xml version='1.0'?>
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry>
            <id>http://arxiv.org/abs/1234.5678v1</id>
            <title> Vision Paper </title>
            <summary>Abstract text</summary>
            <published>2026-03-23T00:00:00Z</published>
            <updated>2026-03-23T00:00:00Z</updated>
            <author><name>Alice</name></author>
            <link title='pdf' href='http://arxiv.org/pdf/1234.5678v1'/>
            <category term='cs.CV'/>
          </entry>
        </feed>\"\"\"
    )
    records = ArxivSource(base_url="https://example.test").fetch()
    assert records[0].source_paper_id == "1234.5678v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_arxiv_source.py -q
```

Expected: FAIL because `ArxivSource` does not exist.

- [ ] **Step 3: Implement source base class and arXiv adapter**

Implement:

- `BaseSource.fetch() -> list[PaperRecord]`
- `ArxivSource.fetch()`
- Atom XML parsing
- category filtering
- lookback window query building

Minimal parse rule:

```python
source_paper_id = entry_id.rsplit("/", 1)[-1]
title = " ".join(title.split())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_arxiv_source.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/sources/__init__.py app/sources/base.py app/sources/arxiv.py tests/test_arxiv_source.py
git commit -m "feat: add arxiv source adapter"
```

## Task 6: Implement OpenReview Source Adapter

**Files:**
- Create: `app/sources/openreview.py`
- Test: `tests/test_openreview_source.py`

- [ ] **Step 1: Write failing OpenReview parsing test**

```python
from app.sources.openreview import OpenReviewSource


def test_openreview_source_parses_note_payload(httpx_mock):
    httpx_mock.add_response(
        json={
            "notes": [
                {
                    "id": "note-1",
                    "content": {
                        "title": {"value": "OpenReview Vision Paper"},
                        "abstract": {"value": "Abstract"},
                        "authors": {"value": ["Alice", "Bob"]},
                    },
                    "cdate": 1774224000000,
                    "mdate": 1774224000000,
                    "details": {"pdf": "/pdf/note-1.pdf"},
                    "forum": "forum-1",
                    "venue": "CVPR 2026",
                }
            ]
        }
    )
    records = OpenReviewSource(base_url="https://example.test", venues=["CVPR"]).fetch()
    assert records[0].source_paper_id == "note-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_openreview_source.py -q
```

Expected: FAIL because `OpenReviewSource` does not exist.

- [ ] **Step 3: Implement OpenReview adapter**

Implement:

- venue filtering
- note payload parsing
- millisecond timestamp conversion
- paper URL and PDF URL construction

Minimal mapping rule:

```python
title = note["content"]["title"]["value"]
authors = note["content"].get("authors", {}).get("value", [])
paper_url = f"{base_url}/forum?id={note['forum']}"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_openreview_source.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/sources/openreview.py tests/test_openreview_source.py
git commit -m "feat: add openreview source adapter"
```

## Task 7: Implement Normalization and Pipeline Orchestration

**Files:**
- Create: `app/normalizer.py`
- Create: `app/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline test**

```python
from app.pipeline import run_pipeline
from app.schemas import PaperRecord


class FakeSource:
    name = "arxiv"

    def fetch(self):
        return [
            PaperRecord(
                source="arxiv",
                source_paper_id="1234.5678",
                title="Vision Paper",
                paper_url="https://arxiv.org/abs/1234.5678",
            )
        ]


def test_run_pipeline_inserts_and_returns_summary(tmp_path):
    summary = run_pipeline(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        sources=[FakeSource()],
        notifier=None,
    )
    assert summary.total_new == 1
    assert summary.total_fetched == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: FAIL because pipeline orchestration is missing.

- [ ] **Step 3: Implement normalization and orchestration**

Implement:

- ensure each record gets `dedup_key`
- per-source run accounting
- insert/update decision via `Database`
- summary object for notification stage

Minimal orchestration signature:

```python
def run_pipeline(database_url: str, sources: list, notifier=None) -> PipelineSummary:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/normalizer.py app/pipeline.py tests/test_pipeline.py
git commit -m "feat: add crawler pipeline orchestration"
```

## Task 8: Implement Feishu Notification Module

**Files:**
- Create: `app/notifiers/__init__.py`
- Create: `app/notifiers/feishu_bot.py`
- Test: `tests/test_feishu_bot.py`

- [ ] **Step 1: Write failing notifier tests**

```python
from app.notifiers.feishu_bot import FeishuBotNotifier


def test_feishu_message_contains_new_paper_title():
    notifier = FeishuBotNotifier("https://example.invalid/hook")
    payload = notifier.build_payload(
        summary_title="Daily Digest",
        papers=[{"title": "Vision Paper", "paper_url": "https://example.test/paper"}],
    )
    assert "Vision Paper" in str(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_feishu_bot.py -q
```

Expected: FAIL because notifier is missing.

- [ ] **Step 3: Implement Feishu payload builder and sender**

Implement:

- `build_payload(summary_title, papers, stats)`
- `send(payload)`
- notification truncation to `MAX_NOTIFY_ITEMS`

Minimal payload shape:

```python
{
    "msg_type": "text",
    "content": {
        "text": "AI Vision Papers Daily Digest\n- Vision Paper\nhttps://example.test/paper"
    },
}
```

Use plain text first. Upgrade to card message only after tests pass.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_feishu_bot.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/notifiers/__init__.py app/notifiers/feishu_bot.py tests/test_feishu_bot.py
git commit -m "feat: add feishu bot notifier"
```

## Task 9: Wire `run_once.py` and End-to-End CLI Behavior

**Files:**
- Modify: `run_once.py`
- Test: `tests/test_run_once.py`

- [ ] **Step 1: Replace the bootstrap smoke test with a failing CLI behavior test**

```python
from run_once import main


def test_main_returns_zero_when_pipeline_succeeds(monkeypatch):
    monkeypatch.setattr("run_once.run_pipeline_from_config", lambda: 0)
    assert main() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_run_once.py -q
```

Expected: FAIL because CLI is not wired to pipeline yet.

- [ ] **Step 3: Implement CLI wiring**

Implement:

- load `.env`
- load `config/sources.yaml`
- configure logging
- create enabled source adapters
- instantiate notifier only if webhook exists
- call pipeline
- exit `0` on success, non-zero on fatal startup failure

Minimal shape:

```python
def main() -> int:
    run_pipeline_from_config()
    return 0
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/test_run_once.py tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add run_once.py tests/test_run_once.py
git commit -m "feat: wire single-run crawler entrypoint"
```

## Task 10: Add Deployment Docs and Cron Example

**Files:**
- Modify: `README.md`
- Create: `scripts/setup_cron.example`

- [ ] **Step 1: Write the failing documentation expectation test**

```python
from pathlib import Path


def test_cron_example_file_exists():
    assert Path("scripts/setup_cron.example").exists()
```

Add this test to `tests/test_run_once.py`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_run_once.py -q
```

Expected: FAIL because the cron example file is missing.

- [ ] **Step 3: Add deployment documentation**

Document:

- dependency install command
- `.env` setup
- `config/sources.yaml` edits
- manual run command
- cron setup command

Cron example:

```bash
0 8 * * * cd /root/workspace/paperclaw && /usr/bin/python3 run_once.py >> logs/cron.log 2>&1
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_run_once.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md scripts/setup_cron.example tests/test_run_once.py
git commit -m "docs: add deployment and cron setup instructions"
```

## Task 11: Run MVP Verification Suite

**Files:**
- Verify only: existing project files

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run a local smoke execution without remote side effects**

Run:

```bash
python run_once.py
```

Expected: process exits `0` when config is present and logs startup summary.

- [ ] **Step 3: Review generated SQLite file path and logs**

Check:

```bash
ls -la data
ls -la logs
```

Expected: SQLite file exists after a real run; log directory exists if configured.

- [ ] **Step 4: Commit verification-safe changes only**

```bash
git add .
git commit -m "test: verify ai vision paper crawler mvp"
```

## Notes for the Implementer

- Keep `CVF` as a placeholder file with a clear `NotImplementedError`; do not pull CVF parsing into the MVP.
- Prefer SQLAlchemy Core or lightweight ORM usage; do not introduce Alembic in the first pass.
- Prefer plain text Feishu messages for the MVP; rich cards are optional follow-up work.
- Mock all network calls in unit tests; the full suite should pass offline.
- If `run_once.py` would fail hard when `FEISHU_BOT_WEBHOOK` is unset, treat that as a design bug. Notification should be optional so local dry runs work.
