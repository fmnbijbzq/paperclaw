# Pipeline And Notification Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve per-source failure isolation, surface partial-failure status to the CLI, and make Feishu notification success accounting exact and retry-safe.

**Architecture:** Keep the existing pipeline and notifier structure, but tighten result semantics at each boundary. The pipeline summary becomes the source of truth for partial failures, the notifier validates both HTTP and Feishu business success, and the notification cycle records only the papers actually attempted.

**Tech Stack:** Python, pytest, SQLAlchemy, httpx

---

### Task 1: Pipeline Failure Summary And Exit Code

**Files:**
- Modify: `app/pipeline.py`
- Modify: `run_once.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_pipeline_continues_after_one_source_fails(tmp_path):
    ...

def test_run_pipeline_from_config_returns_non_zero_when_any_source_fails(monkeypatch):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py tests/test_run_once.py -q`
Expected: FAIL because the pipeline still raises on first source failure and the CLI always returns `0`.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class PipelineSummary:
    ...
    failed_sources: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_sources)
```

Update `run_pipeline()` to record failures and continue. Update `run_pipeline_from_config()` to return `1` when `summary.has_failures` is true.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py tests/test_run_once.py -q`
Expected: PASS

### Task 2: Feishu Business Failure Handling

**Files:**
- Modify: `app/notifiers/feishu_bot.py`
- Test: `tests/test_feishu_bot.py`

- [ ] **Step 1: Write the failing test**

```python
def test_feishu_send_raises_when_business_status_is_non_zero():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feishu_bot.py -q`
Expected: FAIL because `send()` currently treats HTTP 200 as success even when `StatusCode != 0`.

- [ ] **Step 3: Write minimal implementation**

```python
result = response.json()
if result.get("StatusCode", 0) != 0:
    raise RuntimeError(...)
return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feishu_bot.py -q`
Expected: PASS

### Task 3: Exact Notification Attempt Accounting

**Files:**
- Modify: `app/notification_pipeline.py`
- Test: `tests/test_notification_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_notification_cycle_only_marks_actually_sent_papers_successful(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_notification_pipeline.py -q`
Expected: FAIL because the cycle records every selected paper as successful even if the notifier truncates the payload.

- [ ] **Step 3: Write minimal implementation**

```python
send_limit = getattr(notifier, "max_items", len(papers))
attempted_papers = papers[:send_limit]
```

Send and record only `attempted_papers`, leaving the remainder pending.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_notification_pipeline.py -q`
Expected: PASS

### Task 4: Final Verification

**Files:**
- Test: `tests/test_pipeline.py`
- Test: `tests/test_run_once.py`
- Test: `tests/test_feishu_bot.py`
- Test: `tests/test_notification_pipeline.py`
- Test: `tests/`

- [ ] **Step 1: Run focused regression tests**

Run: `pytest tests/test_pipeline.py tests/test_run_once.py tests/test_feishu_bot.py tests/test_notification_pipeline.py -q`
Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `pytest -q`
Expected: PASS with the existing integration skip unchanged.
