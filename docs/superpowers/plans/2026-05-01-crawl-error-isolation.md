# Crawl Error Isolation & Retry Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single bad paper must not abort the rest of the source's crawl, must not flip the source's `crawl_runs.status` to `failed`, and must not be silently lost — it goes into a `paper_fetch_failures` queue and is retried on the next run.

**Architecture:** (1) Move the `try/except` in `app/pipeline.py` from per-source to per-paper. (2) Add a `paper_fetch_failures` table, four `Database` methods, and a `retry_pending_failures()` helper called before each source's fetch. (3) Strip unpaired UTF-16 surrogate code points in `app/enrichment/extractor.py:_normalize_text` so the most common known cause of failure (pypdf decoding `\ud835` etc.) is neutralised at the boundary.

**Tech Stack:** Python 3, SQLAlchemy 2 ORM (`Mapped[...]` + `mapped_column`), SQLite, pytest, conda env `paperclaw` driven by `uv`. The codebase uses `from __future__ import annotations`, `pydantic` for `PaperRecord`, and a single `Database` class wrapping a sessionmaker.

**Spec:** `docs/superpowers/specs/2026-05-01-crawl-error-isolation-design.md`

---

## File Structure

| File | New / Modify | Responsibility |
|------|--------------|----------------|
| `app/enrichment/extractor.py` | modify | Add `_strip_unpaired_surrogates`; wire it into `_normalize_text`. |
| `app/models.py` | modify | Add `PaperFetchFailure` ORM class at end of file. |
| `app/storage.py` | modify | Add 4 methods: `record_paper_failure`, `bump_failure_attempts`, `mark_failure_resolved`, `list_pending_failures`. Update the `from app.models import` line. |
| `app/config.py` | modify | Add two settings: `paper_fetch_max_retry_per_run` (default 50), `paper_fetch_max_retry_attempts` (default 5). |
| `app/pipeline.py` | modify | (a) per-paper `try/except` instead of per-source; (b) call `_retry_pending_failures` before each source's fetch; (c) carry `failed_papers` count in `PipelineSummary.per_source[name]`. |
| `tests/test_extractor.py` | modify | Add unit tests for `_strip_unpaired_surrogates` and `_normalize_text`'s sanitisation behaviour. |
| `tests/test_storage.py` | modify | Add CRUD tests for the four new `Database` methods, including the `attempts` cap. |
| `tests/test_pipeline.py` | modify | Add tests for per-paper isolation + failure-queue retry round-trip. |
| `CLAUDE.md` | modify | Document the failure queue, the two new env vars, and the new CrawlRun semantics. |

No new files are created — every change extends an existing file. This is intentional: the failure queue is a small, focused addition that fits the existing single-`Database`-class pattern.

---

## Task A: Surrogate sanitisation in `_normalize_text`

This task is independent and goes first because it is small, easy to verify, and proves the test toolchain works before larger changes.

**Files:**
- Modify: `app/enrichment/extractor.py:186-191`
- Test: `tests/test_extractor.py` (append)

- [ ] **A.1: Write the failing tests**

Append to `tests/test_extractor.py`:

```python
from app.enrichment.extractor import _normalize_text, _strip_unpaired_surrogates


def test_strip_unpaired_surrogates_removes_high_surrogate():
    # \ud835 is the unpaired high surrogate emitted by pypdf for some
    # mathematical-italic glyphs. It must be stripped before the string
    # is handed to SQLite (which encodes to UTF-8 and rejects surrogates).
    assert _strip_unpaired_surrogates("hello\ud835world") == "helloworld"


def test_strip_unpaired_surrogates_removes_low_surrogate():
    assert _strip_unpaired_surrogates("a\udc00b") == "ab"


def test_strip_unpaired_surrogates_keeps_normal_text():
    assert _strip_unpaired_surrogates("hello world 你好") == "hello world 你好"


def test_normalize_text_strips_surrogates_before_whitespace_collapse():
    # Real arxiv PDF case: surrogate sandwiched in normal text. Whitespace
    # is still collapsed afterwards.
    assert _normalize_text("foo  \ud835  bar") == "foo bar"
```

- [ ] **A.2: Run the tests, confirm they fail**

```bash
conda run -n paperclaw pytest tests/test_extractor.py -k surrogate -v
```

Expected: `ImportError: cannot import name '_strip_unpaired_surrogates'` (4 errors).

- [ ] **A.3: Implement `_strip_unpaired_surrogates` and call it from `_normalize_text`**

Edit `app/enrichment/extractor.py`. Add a `re` import at the top of the file (after `from io import BytesIO`):

```python
import re
```

Replace lines 186-191 (the existing `_normalize_text`) with:

```python
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def _strip_unpaired_surrogates(value: str) -> str:
    """Remove UTF-16 surrogate code points from a Python str.

    Python str can hold any code point including bare surrogates; UTF-8
    encoding rejects them. PDF extractors (notably pypdf on mathematical
    italic SMP code points like 𝑥 = U+1D465) sometimes emit unpaired
    high surrogates (e.g. \\ud835). Strip them at the boundary so they
    cannot reach SQLite or downstream JSON.
    """
    return _SURROGATE_RE.sub("", value)


def _normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _strip_unpaired_surrogates(value)
    lines = [" ".join(line.split()) for line in cleaned.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized = "\n".join(line for line in lines if line).strip()
    return normalized or None
```

- [ ] **A.4: Run the new tests, confirm they pass**

```bash
conda run -n paperclaw pytest tests/test_extractor.py -k surrogate -v
```

Expected: 4 passed.

- [ ] **A.5: Run the full extractor test file, confirm no regression**

```bash
conda run -n paperclaw pytest tests/test_extractor.py -v
```

Expected: all tests pass (the existing 4 + the new 4).

- [ ] **A.6: Commit**

```bash
git add app/enrichment/extractor.py tests/test_extractor.py
git commit -m "$(cat <<'EOF'
正确性：清洗未配对 UTF-16 代理位，避免 pypdf 输出的 \ud835 类字符
导致下游 SQLite UTF-8 编码失败

在 _normalize_text 入口处用正则剥掉 \ud800-\udfff，并把这个动作单独
暴露成 _strip_unpaired_surrogates 以便单测。所有走 TextExtractor 的
路径（pdf/landing page/HTML）都受益。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task B: `PaperFetchFailure` model + 4 `Database` methods

**Files:**
- Modify: `app/models.py` (append at end)
- Modify: `app/storage.py:13` (import) + append methods near the existing crawl-run methods (~line 65)
- Test: `tests/test_storage.py` (append)

- [ ] **B.1: Write the failing tests**

Append to `tests/test_storage.py`:

```python
import json
from app.schemas import PaperRecord


def _make_record(*, source_paper_id: str = "1234.5678") -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        title="Vision Paper",
        abstract="Abstract",
        authors=["Alice"],
        paper_url=f"https://arxiv.org/abs/{source_paper_id}",
    )


def test_record_paper_failure_creates_row_with_attempts_one(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    failure = db.record_paper_failure(
        source="arxiv",
        record=_make_record(),
        error_phase="upsert",
        error=ValueError("bang"),
    )

    assert failure.attempts == 1
    assert failure.source == "arxiv"
    assert failure.source_paper_id == "1234.5678"
    assert failure.error_phase == "upsert"
    assert "bang" in failure.error_message
    assert failure.resolved_at is None
    # raw_payload must be a JSON-roundtrippable dict carrying the full record
    assert failure.raw_payload["title"] == "Vision Paper"
    assert failure.raw_payload["authors"] == ["Alice"]


def test_record_paper_failure_is_idempotent_per_source_and_paper(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    db.record_paper_failure(
        source="arxiv",
        record=_make_record(),
        error_phase="normalize",
        error=ValueError("first"),
    )
    second = db.record_paper_failure(
        source="arxiv",
        record=_make_record(),
        error_phase="upsert",
        error=ValueError("second"),
    )

    assert second.attempts == 2
    assert second.error_phase == "upsert"
    assert "second" in second.error_message
    pending = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending) == 1


def test_list_pending_failures_excludes_resolved_and_exhausted(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    a = db.record_paper_failure(
        source="arxiv",
        record=_make_record(source_paper_id="aa"),
        error_phase="upsert",
        error=ValueError("a"),
    )
    b = db.record_paper_failure(
        source="arxiv",
        record=_make_record(source_paper_id="bb"),
        error_phase="upsert",
        error=ValueError("b"),
    )
    db.record_paper_failure(
        source="arxiv",
        record=_make_record(source_paper_id="cc"),
        error_phase="upsert",
        error=ValueError("c"),
    )

    db.mark_failure_resolved(a.failure_id)
    # bump b past max_attempts
    for _ in range(5):
        db.bump_failure_attempts(b.failure_id, error_phase="upsert", error=ValueError("again"))

    pending = db.list_pending_failures(source="arxiv", limit=10, max_attempts=5)
    pending_ids = {row.source_paper_id for row in pending}
    assert pending_ids == {"cc"}


def test_list_pending_failures_filters_by_source(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    db.record_paper_failure(
        source="arxiv", record=_make_record(source_paper_id="a1"),
        error_phase="upsert", error=ValueError("x"),
    )
    db.record_paper_failure(
        source="openreview",
        record=PaperRecord(
            source="openreview", source_paper_id="o1",
            title="t", paper_url="https://openreview.net/forum?id=o1",
        ),
        error_phase="upsert", error=ValueError("y"),
    )

    arxiv_pending = db.list_pending_failures(source="arxiv", limit=10)
    or_pending = db.list_pending_failures(source="openreview", limit=10)
    assert {f.source_paper_id for f in arxiv_pending} == {"a1"}
    assert {f.source_paper_id for f in or_pending} == {"o1"}


def test_mark_failure_resolved_sets_resolved_at(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    failure = db.record_paper_failure(
        source="arxiv", record=_make_record(),
        error_phase="upsert", error=ValueError("bang"),
    )
    assert failure.resolved_at is None

    resolved = db.mark_failure_resolved(failure.failure_id)
    assert resolved.resolved_at is not None
    assert db.list_pending_failures(source="arxiv", limit=10) == []
```

- [ ] **B.2: Run the tests, confirm they fail with import / attribute errors**

```bash
conda run -n paperclaw pytest tests/test_storage.py -k 'failure' -v
```

Expected: failures with `AttributeError: 'Database' object has no attribute 'record_paper_failure'` (5 errors).

- [ ] **B.3: Add the `PaperFetchFailure` model**

Append to `app/models.py` (after the `DestinationRecord` class):

```python
class PaperFetchFailure(Base):
    """A paper whose ingestion failed mid-pipeline. Retried on next run."""
    __tablename__ = "paper_fetch_failures"
    __table_args__ = (
        UniqueConstraint("source", "source_paper_id", name="uq_paper_fetch_failures_source_id"),
    )

    failure_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_paper_id: Mapped[str] = mapped_column(String(255), nullable=False)
    error_phase: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    first_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **B.4: Update the storage import line**

Edit `app/storage.py:13`. Replace:

```python
from app.models import Base, CrawlRun, DestinationRecord, EditorialDraft, EditorialRun, ExportRecord, Notification, Paper, PaperInsight, PaperVersion, PipelineTask, SummarizationRun
```

with:

```python
from app.models import Base, CrawlRun, DestinationRecord, EditorialDraft, EditorialRun, ExportRecord, Notification, Paper, PaperFetchFailure, PaperInsight, PaperVersion, PipelineTask, SummarizationRun
```

- [ ] **B.5: Add the four `Database` methods**

Insert these methods into `app/storage.py` after `finish_crawl_run` (around line 66). Make sure they live inside the `Database` class:

```python
    def record_paper_failure(
        self,
        *,
        source: str,
        record: PaperRecord,
        error_phase: str,
        error: BaseException,
    ) -> PaperFetchFailure:
        """Insert a new fetch-failure row, or bump attempts on the existing one
        for the same (source, source_paper_id)."""
        message = f"{type(error).__name__}: {error}"
        payload = record.model_dump(mode="json")
        with self._session() as session:
            existing = session.scalar(
                select(PaperFetchFailure).where(
                    PaperFetchFailure.source == source,
                    PaperFetchFailure.source_paper_id == record.source_paper_id,
                )
            )
            if existing is None:
                row = PaperFetchFailure(
                    source=source,
                    source_paper_id=record.source_paper_id,
                    error_phase=error_phase,
                    error_message=message,
                    attempts=1,
                    raw_payload=payload,
                )
                session.add(row)
                session.commit()
                return row

            existing.attempts += 1
            existing.error_phase = error_phase
            existing.error_message = message
            existing.raw_payload = payload
            existing.last_failed_at = utc_now()
            existing.resolved_at = None
            session.commit()
            return existing

    def bump_failure_attempts(
        self,
        failure_id: int,
        *,
        error_phase: str,
        error: BaseException,
    ) -> PaperFetchFailure:
        message = f"{type(error).__name__}: {error}"
        with self._session() as session:
            row = session.get(PaperFetchFailure, failure_id)
            if row is None:
                raise ValueError(f"paper fetch failure {failure_id} does not exist")
            row.attempts += 1
            row.error_phase = error_phase
            row.error_message = message
            row.last_failed_at = utc_now()
            session.commit()
            return row

    def mark_failure_resolved(self, failure_id: int) -> PaperFetchFailure:
        with self._session() as session:
            row = session.get(PaperFetchFailure, failure_id)
            if row is None:
                raise ValueError(f"paper fetch failure {failure_id} does not exist")
            row.resolved_at = utc_now()
            session.commit()
            return row

    def list_pending_failures(
        self,
        *,
        source: str,
        limit: int,
        max_attempts: int = 5,
    ) -> list[PaperFetchFailure]:
        with self._session() as session:
            stmt = (
                select(PaperFetchFailure)
                .where(
                    PaperFetchFailure.source == source,
                    PaperFetchFailure.resolved_at.is_(None),
                    PaperFetchFailure.attempts < max_attempts,
                )
                .order_by(PaperFetchFailure.first_failed_at.asc())
                .limit(limit)
            )
            return list(session.scalars(stmt))
```

- [ ] **B.6: Run the storage tests, confirm they pass**

```bash
conda run -n paperclaw pytest tests/test_storage.py -k 'failure' -v
```

Expected: 5 passed.

- [ ] **B.7: Run the full storage test file, confirm no regression**

```bash
conda run -n paperclaw pytest tests/test_storage.py -v
```

Expected: all tests pass.

- [ ] **B.8: Commit**

```bash
git add app/models.py app/storage.py tests/test_storage.py
git commit -m "$(cat <<'EOF'
模型 + 存储：新增 paper_fetch_failures 表与四个 Database 方法

record_paper_failure / bump_failure_attempts / mark_failure_resolved /
list_pending_failures。一篇论文一行（source, source_paper_id 唯一）；
重复 record 时增加 attempts 而不是新插行；attempts >= max_attempts 后
list_pending_failures 不再返回，等待人工介入。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task C: Per-paper isolation in `pipeline.py` + `_retry_pending_failures`

This is the largest behavioural change. We rewrite the body of `run_pipeline`'s source loop.

**Files:**
- Modify: `app/pipeline.py:60-149` (the source loop body)
- Test: `tests/test_pipeline.py` (append)

- [ ] **C.1: Read the current pipeline body once before editing**

Re-read `app/pipeline.py:60-149` so the diff in step C.4 is unsurprising. The existing flow is: outer try → fetch → inner for-loop with normalize+upsert+insight → finish_crawl_run(success). The replacement keeps that shape but changes which exceptions go where.

- [ ] **C.2: Write the failing tests**

Append to `tests/test_pipeline.py`:

```python
from app.schemas import PaperRecord
from app.storage import Database


class _OneGoodOneBadSource:
    """First record is fine, second triggers a writable upsert error mid-loop."""
    name = "arxiv"

    def fetch(self):
        return [
            PaperRecord(
                source="arxiv",
                source_paper_id="good-1",
                title="Good Paper",
                abstract="ok",
                authors=["Alice"],
                paper_url="https://arxiv.org/abs/good-1",
            ),
            PaperRecord(
                source="arxiv",
                source_paper_id="bad-2",
                title="Bad Paper",
                abstract="will explode at upsert time",
                # \ud835 will be sanitised by extractor BUT we feed it
                # directly into PaperRecord.full_text here so we can
                # exercise the per-paper try/except path with a real
                # SQLite encoding error.
                full_text="text with \ud835 surrogate",
                authors=["Bob"],
                paper_url="https://arxiv.org/abs/bad-2",
            ),
            PaperRecord(
                source="arxiv",
                source_paper_id="good-3",
                title="Third Paper",
                abstract="comes after the bad one",
                authors=["Carol"],
                paper_url="https://arxiv.org/abs/good-3",
            ),
        ]


def test_one_bad_paper_does_not_abort_the_source_run(tmp_path):
    """Spec acceptance: a single paper failing must not flip CrawlRun to
    failed, must not skip subsequent papers, and must record the failure."""
    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    summary = run_pipeline(
        database_url=database_url,
        sources=[_OneGoodOneBadSource()],
        notifier=None,
    )

    db = Database(database_url)

    # The two good papers got in.
    assert db.count_papers() == 2
    # CrawlRun for arxiv is success because source.fetch() worked.
    runs = db.list_crawl_runs(source="arxiv", limit=10)
    assert runs[0].status == "success"
    assert runs[0].fetched_count == 3
    assert runs[0].new_count == 2
    # The bad paper sits in the failure queue.
    pending = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending) == 1
    assert pending[0].source_paper_id == "bad-2"
    assert pending[0].attempts == 1
    # And the summary surfaces the per-source failure count.
    assert summary.per_source["arxiv"]["failed_papers"] == 1
    assert summary.per_source["arxiv"]["status"] == "success"


class _NoOpSource:
    """A source that fetches nothing — used to test the retry path
    independently of new fetches."""
    name = "arxiv"

    def fetch(self):
        return []


def test_pending_failure_is_retried_and_resolved_on_next_run(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path/'papers.db'}"

    # Round 1: the bad paper enters the failure queue.
    run_pipeline(
        database_url=database_url,
        sources=[_OneGoodOneBadSource()],
        notifier=None,
    )

    db = Database(database_url)
    pending_before = db.list_pending_failures(source="arxiv", limit=10)
    assert len(pending_before) == 1
    bad_id = pending_before[0].failure_id

    # Round 2: simulate the surrogate fix being in place by having the
    # storage layer accept the previously-bad payload. We monkeypatch
    # the extractor's surrogate cleaner into the failure's raw_payload.full_text.
    from app.enrichment.extractor import _strip_unpaired_surrogates
    with db._session() as session:
        from app.models import PaperFetchFailure
        row = session.get(PaperFetchFailure, bad_id)
        payload = dict(row.raw_payload)
        payload["full_text"] = _strip_unpaired_surrogates(payload["full_text"])
        row.raw_payload = payload
        session.commit()

    # No new fetch this round; only the retry path should fire.
    run_pipeline(
        database_url=database_url,
        sources=[_NoOpSource()],
        notifier=None,
    )

    pending_after = db.list_pending_failures(source="arxiv", limit=10)
    assert pending_after == []
    # The previously-failed paper is now in the papers table.
    assert db.count_papers() == 3
```

- [ ] **C.3: Run the tests, confirm they fail**

```bash
conda run -n paperclaw pytest tests/test_pipeline.py::test_one_bad_paper_does_not_abort_the_source_run tests/test_pipeline.py::test_pending_failure_is_retried_and_resolved_on_next_run -v
```

Expected: both fail. The first fails because the existing pipeline marks the run `failed`; the second fails because there is no retry path.

- [ ] **C.4: Replace the source loop body in `app/pipeline.py`**

Replace lines 60-149 in `app/pipeline.py` (the entire `for source in sources:` block) with this:

```python
    # 统计启用的数据源数量
    LOGGER.info(f"开始处理 {len(sources)} 个数据源...")

    max_retry_per_run = int(os.environ.get("PAPER_FETCH_MAX_RETRY_PER_RUN", "50"))
    max_retry_attempts = int(os.environ.get("PAPER_FETCH_MAX_RETRY_ATTEMPTS", "5"))

    for source in sources:
        source_name = getattr(source, "name", source.__class__.__name__.lower())
        LOGGER.info(f"「数据源 [{source_name}]」开始处理...")

        crawl_run = db.start_crawl_run(source_name)
        fetched_count = 0
        new_count = 0
        failed_papers = 0

        # First: replay any pending failures from prior runs. They count
        # as new_count if the upsert creates a row, but they do not count
        # as fetched_count (fetched_count tracks what the source returned
        # this run).
        retry_new, retry_failed = _retry_pending_failures(
            db=db,
            source_name=source_name,
            summarizer=summarizer,
            summary=summary,
            force_resummarize=force_resummarize,
            max_retry=max_retry_per_run,
            max_attempts=max_retry_attempts,
            sum_state=_SumRunState(),  # forwarded into per-paper handler
        )
        new_count += retry_new
        failed_papers += retry_failed

        try:
            LOGGER.info(f"  正在从 {source_name} 抓取论文...")
            fetched_records = source.fetch()
        except Exception as exc:
            # Only the source-level fetch failure flips the CrawlRun to
            # failed. Per-paper failures below do not.
            LOGGER.exception(f"  ✗ {source_name} fetch 阶段失败")
            db.finish_crawl_run(
                crawl_run.run_id,
                status="failed",
                fetched_count=fetched_count,
                new_count=new_count,
                error_message=str(exc),
            )
            summary.per_source[source_name] = {
                "status": "failed",
                "fetched": fetched_count,
                "new": new_count,
                "failed_papers": failed_papers,
                "error": str(exc),
            }
            summary.failed_sources.append(source_name)
            continue

        fetched_count = len(fetched_records)
        summary.total_fetched += fetched_count
        LOGGER.info(f"  成功抓取 {fetched_count} 条记录")
        if fetched_count == 0:
            LOGGER.warning(f"  警告：{source_name} 返回 0 条记录")

        for i, record in enumerate(fetched_records, 1):
            try:
                created = _ingest_one_paper(
                    db=db,
                    record=record,
                    summarizer=summarizer,
                    summary=summary,
                    force_resummarize=force_resummarize,
                    sum_state=_SumRunState(),
                )
            except Exception as per_paper_exc:
                LOGGER.warning(
                    "  [%s/%s] %s -> 失败：%s（已写入失败队列，下次重试）",
                    i, fetched_count, record.title, per_paper_exc,
                )
                # error_phase is set inside _ingest_one_paper via attribute
                # on the exception; default to 'unknown' if absent.
                phase = getattr(per_paper_exc, "_paperclaw_phase", "unknown")
                db.record_paper_failure(
                    source=source_name,
                    record=record,
                    error_phase=phase,
                    error=per_paper_exc,
                )
                failed_papers += 1
                continue

            LOGGER.info(
                "  [%s/%s] %s -> %s",
                i, fetched_count, record.title,
                "新增入库" if created else "已存在，跳过新增",
            )
            if created:
                summary.total_new += 1
                new_count += 1

        db.finish_crawl_run(
            crawl_run.run_id,
            status="success",
            fetched_count=fetched_count,
            new_count=new_count,
        )
        summary.per_source[source_name] = {
            "status": "success",
            "fetched": fetched_count,
            "new": new_count,
            "failed_papers": failed_papers,
        }
        LOGGER.info(
            f"  ✓ {source_name} 处理完成：抓 {fetched_count} 条，"
            f"新增 {new_count} 条，失败入队 {failed_papers} 条"
        )
```

- [ ] **C.5: Add the helper functions and the `os` + `dataclass` imports**

At the top of `app/pipeline.py`, add `import os` and tighten the imports. The current top is:

```python
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
import logging
```

Add `import os` after `import logging`:

```python
import os
```

(Note: `Iterable` is already imported and unused after our edit; do not remove it in this task — that is a separate cleanup.)

Then, immediately above the `def run_pipeline(...)` line, add the two helpers + the small state container (the `_SumRunState` is a dataclass so the per-paper helper can mutate counters that need to be visible to the outer scope; this avoids passing four mutable counters around):

```python
@dataclass
class _SumRunState:
    """Per-source mutable counters for the SummarizationRun bookkeeping."""
    papers_processed: int = 0
    insights_generated: int = 0
    failures: int = 0


def _ingest_one_paper(
    *,
    db: Database,
    record: PaperRecord,
    summarizer: SummarizationService,
    summary: PipelineSummary,
    force_resummarize: bool,
    sum_state: _SumRunState,
) -> bool:
    """Run normalize -> upsert -> insight for a single record. Returns True
    if the upsert created a new paper. Tags any raised exception with the
    phase name so the outer loop can record it in the failure queue."""
    try:
        try:
            normalized = normalize_paper(record)
        except Exception as exc:
            exc._paperclaw_phase = "normalize"  # type: ignore[attr-defined]
            raise
        try:
            result = db.upsert_paper_with_status(normalized)
        except Exception as exc:
            exc._paperclaw_phase = "upsert"  # type: ignore[attr-defined]
            raise

        if result.created:
            summary.new_papers.append(normalized)

        # Insight generation has its own existing try/except — it does not
        # propagate failures up. Keep that behaviour: a failed insight does
        # not push the paper into the failure queue.
        try:
            existing = db.get_paper_insight(paper_id=result.paper.paper_id)
            needs_insight = (
                force_resummarize
                or existing is None
                or bool(getattr(existing, "is_placeholder", True))
            )
            if needs_insight:
                insight = summarizer.generate(normalized)
                db.upsert_paper_insight(paper_id=result.paper.paper_id, insight=insight)
                summary.total_insighted += 1
                sum_state.insights_generated += 1
        except Exception as insight_exc:
            LOGGER.warning("  论文总结失败 [%s]: %s", normalized.title, insight_exc)
            sum_state.failures += 1
        finally:
            sum_state.papers_processed += 1

        return result.created
    except Exception:
        # propagate after the phase is tagged
        raise


def _retry_pending_failures(
    *,
    db: Database,
    source_name: str,
    summarizer: SummarizationService,
    summary: PipelineSummary,
    force_resummarize: bool,
    max_retry: int,
    max_attempts: int,
    sum_state: _SumRunState,
) -> tuple[int, int]:
    """Replay up to `max_retry` pending failures for this source. Returns
    (newly_inserted_count, still_failing_count)."""
    pending = db.list_pending_failures(
        source=source_name,
        limit=max_retry,
        max_attempts=max_attempts,
    )
    if not pending:
        return (0, 0)

    LOGGER.info(f"  从失败队列重放 {len(pending)} 篇待重试论文…")
    new_count = 0
    failed_again = 0
    for failure in pending:
        try:
            record = PaperRecord.model_validate(failure.raw_payload)
        except Exception as deser_exc:
            LOGGER.warning(
                "  重试反序列化失败 (failure_id=%s): %s",
                failure.failure_id, deser_exc,
            )
            db.bump_failure_attempts(
                failure.failure_id,
                error_phase="deserialise",
                error=deser_exc,
            )
            failed_again += 1
            continue

        try:
            created = _ingest_one_paper(
                db=db,
                record=record,
                summarizer=summarizer,
                summary=summary,
                force_resummarize=force_resummarize,
                sum_state=sum_state,
            )
        except Exception as exc:
            phase = getattr(exc, "_paperclaw_phase", "unknown")
            db.bump_failure_attempts(failure.failure_id, error_phase=phase, error=exc)
            LOGGER.warning(
                "  重试仍失败 (failure_id=%s, attempts=%s): %s",
                failure.failure_id, failure.attempts + 1, exc,
            )
            failed_again += 1
            continue

        db.mark_failure_resolved(failure.failure_id)
        if created:
            summary.total_new += 1
            new_count += 1
            LOGGER.info(
                "  ✓ 重试成功并入库 [%s/%s]",
                record.source, record.source_paper_id,
            )

    return (new_count, failed_again)
```

- [ ] **C.6: Run the new pipeline tests**

```bash
conda run -n paperclaw pytest tests/test_pipeline.py::test_one_bad_paper_does_not_abort_the_source_run tests/test_pipeline.py::test_pending_failure_is_retried_and_resolved_on_next_run -v
```

Expected: 2 passed.

- [ ] **C.7: Run the full pipeline test file, confirm no regression**

```bash
conda run -n paperclaw pytest tests/test_pipeline.py -v
```

Expected: all tests pass (existing ones still green).

- [ ] **C.8: Run the broader test suite**

```bash
conda run -n paperclaw pytest tests/ -q
```

Expected: all default-marker tests pass. (Integration tests excluded by default.)

- [ ] **C.9: Commit**

```bash
git add app/pipeline.py tests/test_pipeline.py
git commit -m "$(cat <<'EOF'
正确性：pipeline 错误隔离从源级下沉到论文级 + 失败队列自动重试

旧行为：循环里任意一篇论文炸都会让整个 source 的 CrawlRun 标 failed，
后续论文被跳过、同轮已 commit 的论文也无法被 summarize。新行为：
source.fetch() 整体失败才标 failed；进入循环后每篇独立 try/except，
异常落到 paper_fetch_failures 表，循环继续；下一次 run_once 在 fetch
之前先重放最多 PAPER_FETCH_MAX_RETRY_PER_RUN 篇待重试论文，成功则
mark_failure_resolved，连续失败 PAPER_FETCH_MAX_RETRY_ATTEMPTS 次后
不再自动重试，留给人工。

PipelineSummary.per_source 增加 failed_papers 字段。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task D: Configuration knobs + `CLAUDE.md` documentation

**Files:**
- Modify: `app/config.py:13-28` (add 2 fields to `AppSettings`)
- Modify: `CLAUDE.md` (configuration table + design considerations)

- [ ] **D.1: Add the two settings fields**

In `app/config.py`, in the `AppSettings` class body (after `pipeline_task_timeout_seconds: int = 1800`), add:

```python
    # 一次 run_once.py 中，每个数据源最多重放多少条历史失败论文。控制
    # 失败队列对单次运行时长的影响。
    paper_fetch_max_retry_per_run: int = 50
    # 单条失败论文连续失败多少次后停止自动重试，留给人工处理。
    paper_fetch_max_retry_attempts: int = 5
```

(Note: pipeline.py reads them via `os.environ` rather than `AppSettings` because `run_pipeline` does not currently take an `AppSettings` parameter; surfacing them on `AppSettings` is for documentation + possible future wiring. This is a deliberate, temporary asymmetry — recorded in the design's "What we explicitly do not do" so it does not get enlarged in this task.)

- [ ] **D.2: Update `CLAUDE.md` configuration table**

In `CLAUDE.md`, find the `.env` configuration table (under "## Configuration"). Append two rows before the `LOG_LEVEL` row:

```markdown
| `PAPER_FETCH_MAX_RETRY_PER_RUN` | Per-source cap on how many queued failures `run_once.py` retries before fetching new records (default 50). |
| `PAPER_FETCH_MAX_RETRY_ATTEMPTS` | After this many consecutive failures, a paper stays in `paper_fetch_failures` but is no longer auto-retried (default 5). |
```

- [ ] **D.3: Update `CLAUDE.md` design considerations**

Append a 7th item to the "## Design Considerations" numbered list:

```markdown
7. **Per-paper error isolation, with a retry queue.** Failures inside `run_pipeline`'s per-source loop are caught at the **paper** level, not the source level. A failed record is recorded in `paper_fetch_failures` with its raw `PaperRecord` JSON; the source's `crawl_runs.status` stays `success` as long as `source.fetch()` itself returned. On the next run, `_retry_pending_failures` replays up to `PAPER_FETCH_MAX_RETRY_PER_RUN` queued papers per source through the same `normalize → upsert → insight` path before the source's new fetch. After `PAPER_FETCH_MAX_RETRY_ATTEMPTS` consecutive failures the row stays in the table for human inspection.
```

- [ ] **D.4: Verify the docs render and commit**

```bash
grep -n "PAPER_FETCH_MAX_RETRY" CLAUDE.md
grep -n "paper_fetch_failures" CLAUDE.md
```

Expected: each grep returns at least one line.

```bash
git add app/config.py CLAUDE.md
git commit -m "$(cat <<'EOF'
配置 + 文档：失败队列两个 env 变量进 AppSettings 与 CLAUDE.md

PAPER_FETCH_MAX_RETRY_PER_RUN（默认 50）和
PAPER_FETCH_MAX_RETRY_ATTEMPTS（默认 5）。CLAUDE.md 加一条新的设计
要点描述 per-paper isolation + retry queue 的语义。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task E: End-to-end verification against the real data sources

This task does not write code. It runs the actual pipeline and asserts the spec's acceptance criteria.

**Files:** none changed.

- [ ] **E.1: Snapshot the database before the run**

```bash
sqlite3 data/papers.db "
SELECT 'papers_total', COUNT(*) FROM papers;
SELECT 'failures_total', COUNT(*) FROM paper_fetch_failures;
SELECT 'last_arxiv_run',
  (SELECT status FROM crawl_runs WHERE source='arxiv' ORDER BY started_at DESC LIMIT 1);
"
```

Save the values mentally. You will compare them after.

- [ ] **E.2: Run `run_once.py` (round 1)**

```bash
conda run -n paperclaw python run_once.py 2>&1 | tee logs/dryrun-round1.log
```

This will take ~10 minutes (PDF text extraction is slow; that is a separate issue and not in this plan's scope).

- [ ] **E.3: Verify spec acceptance criteria 1**

```bash
sqlite3 data/papers.db "
SELECT source, status, fetched_count, new_count, error_message
FROM crawl_runs
ORDER BY started_at DESC
LIMIT 3;
"
```

Expected for the most recent arxiv row:

- `status = 'success'` (NOT failed — this is the headline fix)
- `fetched_count = 100`
- `new_count >= 0` (varies by what's already in the DB)
- `error_message` empty

```bash
sqlite3 data/papers.db "
SELECT source, COUNT(*) FROM paper_fetch_failures
WHERE resolved_at IS NULL
GROUP BY source;
"
```

If the surrogate fix from Task A is in place, expected: `0` rows (the fix neutralised the bug at the boundary). If a different per-paper error appears, that is acceptable — the pending row(s) in this table are the proof that the failure queue is working.

- [ ] **E.4: Run `run_once.py` (round 2) to exercise the retry path**

```bash
conda run -n paperclaw python run_once.py 2>&1 | tee logs/dryrun-round2.log
```

- [ ] **E.5: Verify spec acceptance criteria 2**

```bash
sqlite3 data/papers.db "
SELECT failure_id, source, source_paper_id, attempts,
       resolved_at IS NOT NULL AS is_resolved
FROM paper_fetch_failures
ORDER BY first_failed_at DESC
LIMIT 10;
"
```

Expected: each row from round 1 either has `is_resolved = 1` (the surrogate fix made the retry succeed) or has `attempts >= 2` (the retry was attempted but the paper still fails for some other reason — also acceptable, the queue is functioning).

- [ ] **E.6: Verify the dashboard view**

If the API server is running locally:

```bash
curl -s http://localhost:8000/pipeline/runs/crawl?source=arxiv | head -c 500
```

Expected: the most recent arxiv item has `"status":"success"`.

- [ ] **E.7: Inspect logs for the new behaviour**

```bash
grep -E '失败入队|从失败队列重放' logs/dryrun-round1.log logs/dryrun-round2.log
```

Expected: at least one "失败入队 N 条" line in round 1 (if there were per-paper failures), and at least one "从失败队列重放 N 篇" line in round 2.

- [ ] **E.8: If everything passes, no further commit**

This task only verifies; nothing to commit. If a real bug surfaces here, file it and decide whether to extend this plan or open a follow-up. Do not silently patch.

---

## Self-Review (run by author after writing this plan)

**Spec coverage:**
- [x] §1 "Move error isolation from per-source to per-paper" → Task C
- [x] §2 `paper_fetch_failures` table → Task B
- [x] §3 retry on next run, attempts cap, per-run cap → Task B (storage) + Task C (pipeline call) + Task D (env vars)
- [x] §4 CrawlRun semantics (`success` if fetch returned) + `failed_papers` in summary → Task C
- [x] §5 `_strip_unpaired_surrogates` in `_normalize_text` → Task A
- [x] Configuration env vars → Task D
- [x] File-level changes table from spec matches the file structure section here.
- [x] Acceptance criteria 1 & 2 → Task E.

**Placeholder scan:** no TBD/TODO; every code block is complete; commands have expected output; type names (`PaperFetchFailure`, `PaperRecord`, `Database`) and method names (`record_paper_failure`, `bump_failure_attempts`, `mark_failure_resolved`, `list_pending_failures`, `_ingest_one_paper`, `_retry_pending_failures`, `_SumRunState`) are consistent across tasks.

**Type consistency:** `_SumRunState` is defined in C.5 and consumed in C.4 calls; `_ingest_one_paper` returns `bool` (`created`) and is consumed both directly (C.4) and inside `_retry_pending_failures` (C.5); `db.list_pending_failures` returns `list[PaperFetchFailure]` and is consumed in C.5 by attribute access (`.failure_id`, `.raw_payload`, `.attempts`).

One known asymmetry, called out explicitly in D.1: `pipeline.py` reads the two env vars via `os.environ` instead of via `AppSettings`. This is intentional and minimal — `run_pipeline` does not currently accept an `AppSettings` argument, and rewiring its signature is out of scope for this plan.
