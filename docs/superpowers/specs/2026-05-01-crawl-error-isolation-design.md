# Crawl Error Isolation & Retry Queue — Design

**Date:** 2026-05-01
**Topic:** Make `run_once.py` actually persist crawled papers in the presence of per-paper failures, by isolating errors at the paper level and queuing failed items for later retry.

## Background

A dry-run of `run_once.py` against the current code (2026-05-01) showed:

| Source | API call | Insertions | CrawlRun status | Why |
|--------|----------|-----------:|-----------------|-----|
| arXiv | OK | **84 of 100** | `failed` | A single paper triggered `'utf-8' codec can't encode character '\ud835': surrogates not allowed` mid-loop, aborting the whole source. |
| OpenReview | OK | **158 of 158** | `success` | No bad records this run. (Earlier 301 in DB was from a stale base URL no longer in the code.) |
| CVF | n/a | n/a | n/a | `enabled: false` in `config/sources.yaml`. |

The behaviour the user observed as "crawler does not fetch papers" is in fact:

1. Papers are getting fetched and inserted (the database now has 245 rows).
2. But `crawl_runs.status='failed'` causes downstream systems (and the operator) to read the run as a failure, masking the partial success.
3. Worse, **the next time `run_once.py` runs, the 16 papers that were skipped after the bad record are simply forgotten** — they were never even attempted to be inserted.

## Goal

A single bad paper must not:

1. Cause the rest of its source's papers to be skipped.
2. Cause the source's `crawl_runs.status` to be `failed`.
3. Be lost. The pipeline must remember it and retry it on the next run.

Out of scope (explicitly): performance of `_fetch_full_text` (PDF download is slow but not the cause of "no papers"), arXiv UA / backoff (no 429 in current run), CVF activation (untouched configuration).

## Root Cause of the Surrogate Failure

```
ArxivSource._fetch_full_text(pdf_url)
  → TextExtractor.extract_pdf_text(url)
  → pypdf PdfReader → page.extract_text()
        → Returns a Python str containing isolated UTF-16 high surrogates
          (e.g. '\ud835') without their paired low surrogates. This happens
          when PDFs encode mathematical italic glyphs as Unicode SMP code
          points (𝑥 = U+1D465 = ud835 dc65) and pypdf decodes them
          inconsistently.
  → _normalize_text leaves the string unchanged
  → PaperRecord.full_text contains '\ud835'
  → SQLAlchemy / SQLite tries to encode the str as UTF-8
  → UnicodeEncodeError raised inside db.upsert_paper_with_status(...)
  → Caught by the source-level try/except in pipeline.py (line 133)
  → Whole source CrawlRun marked failed, loop continues to next source
```

So there are two separate bugs:

- **Architectural:** error isolation in `pipeline.py` is at the wrong granularity (per-source, should be per-paper).
- **Defensive:** `_normalize_text` does not sanitise the kind of strings PDF extractors are known to produce.

We fix both.

## Design

### 1. Move error isolation from per-source to per-paper

In `app/pipeline.py`, the inner loop currently looks like:

```python
try:
    fetched_records = source.fetch()
    for record in fetched_records:
        normalized = normalize_paper(record)
        result = db.upsert_paper_with_status(normalized)
        # ... insight generation ...
except Exception:
    db.finish_crawl_run(..., status="failed", ...)
    continue
```

The new shape:

```python
try:
    fetched_records = source.fetch()
except Exception:
    # Whole source failed (e.g. network error, API down).
    # Crawl run is genuinely failed.
    db.finish_crawl_run(..., status="failed", ...)
    continue

failed_papers = 0
for record in fetched_records:
    phase = "normalize"
    try:
        normalized = normalize_paper(record)
        phase = "upsert"
        result = db.upsert_paper_with_status(normalized)
        phase = "insight"
        # ... insight generation; existing try around it stays for back-compat ...
    except Exception as exc:
        db.record_paper_failure(
            source=source_name,
            record=record,
            error_phase=phase,
            error=exc,
        )
        failed_papers += 1
        continue

db.finish_crawl_run(..., status="success", ...)  # API call worked
summary.per_source[source_name]["failed_papers"] = failed_papers
```

The outer try/except is kept, but it only fires when `source.fetch()` itself raises (network, parse error on the whole feed). Once we have `fetched_records` in hand, the source's API obligation is met and the run is `success`; per-paper failures are reported via the failure queue and `summary`.

### 2. Add a `paper_fetch_failures` table

```python
class PaperFetchFailure(Base):
    __tablename__ = "paper_fetch_failures"
    failure_id      = Column(Integer, primary_key=True, autoincrement=True)
    source          = Column(String(50),  nullable=False)
    source_paper_id = Column(String(255), nullable=False)
    error_phase     = Column(String(32),  nullable=False)  # 'normalize'|'upsert'|'insight'
    error_message   = Column(Text,        nullable=False)
    attempts        = Column(Integer,     nullable=False, default=1)
    raw_payload     = Column(JSON,        nullable=False)  # serialised PaperRecord
    first_failed_at = Column(DateTime(timezone=True), nullable=False)
    last_failed_at  = Column(DateTime(timezone=True), nullable=False)
    resolved_at     = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("source", "source_paper_id", name="uq_paper_fetch_failures_source_id"),
    )
```

Why a dedicated table:

- Single-table COUNT to know "how many papers are stuck."
- Doesn't pollute `papers` (avoids a `status` column that every existing query would have to filter on).
- Marking via `resolved_at` keeps the historical record for debugging — we never DELETE a row, only set `resolved_at`.

`raw_payload` stores the full `PaperRecord` (`model_dump(mode="json")`) so retries do not need to re-fetch the source feed — they can replay the exact data that originally failed.

### 3. Retry pending failures at the start of each source's loop

```python
for source in sources:
    crawl_run = db.start_crawl_run(source_name)
    retry_pending_failures(db, source_name, summarizer, summary, ...)  # NEW
    fetched_records = source.fetch()
    # ... existing per-paper loop ...
```

`retry_pending_failures` policy:

- Reads up to `MAX_RETRY_PER_RUN` rows (default 50, env var `PAPER_FETCH_MAX_RETRY_PER_RUN`) where `resolved_at IS NULL` and `attempts < MAX_RETRY_ATTEMPTS` (default 5).
- Re-deserialises `raw_payload` to a `PaperRecord`, runs it through the same `normalize → upsert → insight` pipeline.
- Success → set `resolved_at = now()`, increment `summary.total_new` if the upsert created a row.
- Failure → `attempts += 1`, update `error_message` and `last_failed_at`. After `attempts >= MAX_RETRY_ATTEMPTS` the row stays in the table but is no longer eligible for automatic retry — it is left for human inspection (a future dashboard view, or a `scripts/list_failures.py`, can surface these).

### 4. CrawlRun semantics

- `status` stays `success` / `failed` (no schema change). New definition:
  - `failed`: `source.fetch()` itself raised, or the entire run was aborted before per-paper processing.
  - `success`: at least the source's API call returned a parseable result, regardless of how many individual papers failed.
- Per-paper failures are surfaced in `PipelineSummary.per_source[source_name]["failed_papers"]` and in `pipeline.log` (one warning per paper, with phase + error).

This keeps the dashboard's existing CrawlRuns view useful (red = source genuinely down) while not flagging false negatives for unicode quirks.

### 5. Defence: strip unpaired surrogates in `_normalize_text`

```python
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")

def _strip_unpaired_surrogates(value: str) -> str:
    # Surrogate code points are illegal in well-formed UTF-8 text. PDF
    # extractors occasionally emit them when the source PDF uses Unicode
    # SMP code points (mathematical italic letters etc.) that decode in
    # halves. Drop them so downstream UTF-8 encoding does not blow up.
    return _SURROGATE_RE.sub("", value)
```

Called inside `_normalize_text` before whitespace collapsing. This means any text path that goes through `TextExtractor` is sanitised, not just the arXiv full-text path. So even if a future source emits the same garbage, it will be neutralised at the boundary instead of needing a failure queue entry.

The failure queue and the surrogate fix are both required: the queue handles future unknown failure modes; the surrogate fix prevents the most common known one from filling the queue.

## Schema migration

`app/storage.Database.create_schema()` calls `Base.metadata.create_all()`, which is idempotent and creates new tables on existing databases without altering existing ones. No manual migration needed for SQLite. (For an eventual Postgres migration the same approach applies; the table has no column type that differs between SQLite and Postgres.)

## Configuration additions

Two new environment variables (with sensible defaults so the system works without setting them):

| Variable | Default | Meaning |
|----------|---------|---------|
| `PAPER_FETCH_MAX_RETRY_PER_RUN` | `50` | Max number of failed papers retried per source per run. Bounds run time. |
| `PAPER_FETCH_MAX_RETRY_ATTEMPTS` | `5`  | After this many consecutive failures, the row stays in the table but is no longer auto-retried. |

Documented in `CLAUDE.md` under the Configuration section.

## File-level changes

| File | Change |
|------|--------|
| `app/models.py` | Add `PaperFetchFailure` ORM class. |
| `app/storage.py` | Add `record_paper_failure(source, record, error_phase, error)`, `list_pending_failures(source, limit)`, `mark_failure_resolved(failure_id)`, `bump_failure_attempts(failure_id, error_phase, error)`. |
| `app/pipeline.py` | Replace source-level try/except with per-paper try/except; call `retry_pending_failures` before fetch; track `failed_papers` per source. |
| `app/enrichment/extractor.py` | Add `_strip_unpaired_surrogates`; call from `_normalize_text`. |
| `app/config.py` | Read the two new env vars into `AppSettings`. |
| `tests/test_pipeline.py` | Test: one paper that always raises does not abort the run; the source's CrawlRun is `success`; the failure is recorded in the queue. Test: a paper in the queue is retried on the next run and resolved on success. |
| `tests/test_storage.py` | CRUD tests for the four new `Database` methods, including the `attempts` cap. |
| `tests/test_extractor.py` | Test: `_normalize_text("hello\ud835world")` returns `"helloworld"`. |
| `CLAUDE.md` | Document the failure queue, the new env vars, and the new CrawlRun semantics. |

## What we explicitly do not do

- Do not change `_fetch_full_text` to be lazy / async. The synchronous PDF download makes runs slow (~12 min) but does not cause "no papers." Fixing this is a separate, larger refactor; tracked as future work.
- Do not add arXiv UA / backoff. This run did not 429.
- Do not enable CVF. User has not asked for it.
- Do not add a "partial" status to `crawl_runs`. The `failed_papers` counter on the in-memory summary is sufficient for the dashboard, and not changing the column avoids touching every reader.
- Do not modify OpenReview / CVF source adapters.

## Acceptance criteria

1. Running `python run_once.py` against the current arXiv data set produces:
   - `crawl_runs.status='success'` for arXiv.
   - All 84 papers from before the bad record still inserted.
   - The bad record(s) recorded in `paper_fetch_failures` with `attempts=1`.
   - The papers that came after the bad record (16 in the dry-run) also inserted (because the loop did not abort).
2. Running `python run_once.py` again with the surrogate fix in place causes the queued failure to be retried, succeed (because `_normalize_text` now strips the offending characters), and `resolved_at` to be filled in.
3. All existing tests pass; the new tests in the three test files pass.
4. The dashboard's `/pipeline/runs/crawl` endpoint shows arXiv as `success` for the run.
