# Paperclaw Pipeline Task System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable, API-driven pipeline task system so Paperclaw can trigger crawl, insight generation, editorial draft generation, and optional Feishu notification from the dashboard.

**Architecture:** Store task state in a new `pipeline_tasks` table, expose task CRUD/control through `/pipeline/tasks`, and execute tasks through a single in-process FIFO worker. The worker reuses existing script-level building blocks and keeps export manual.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite JSON columns, pytest, Next.js App Router, React, TypeScript, Node test runner

---

## File Map

- Create `app/tasks/__init__.py`: task package exports.
- Create `app/tasks/pipeline_tasks.py`: task runner, task execution orchestration, source factory helpers.
- Modify `app/models.py`: add `PipelineTask` model.
- Modify `app/storage.py`: add pipeline task lifecycle methods and SQLite migration for existing databases.
- Modify `app/api/schemas.py`: add task request/response schemas.
- Modify `app/api/routes/pipeline.py`: add `/pipeline/tasks` endpoints.
- Modify `app/api/app.py`: construct and attach a runner to app state.
- Create `tests/test_pipeline_tasks.py`: storage and runner behavior.
- Modify `tests/test_api_pipeline.py`: API endpoint behavior.
- Modify `frontend/lib/types.ts`: task types.
- Modify `frontend/lib/api-contracts.ts`: task API contracts.
- Modify `frontend/lib/data-sources/http/shared.ts`: add POST helper.
- Modify `frontend/lib/data-sources/http/pipeline.ts`: add task HTTP methods.
- Modify `frontend/lib/data-sources/demo/pipeline.ts`: add task fixtures and simulated task creation.
- Modify `frontend/lib/repositories/pipeline.ts`: expose task methods.
- Modify `frontend/lib/queries.ts`: expose task query/action wrappers.
- Create `frontend/components/pipeline-task-control.tsx`: client control and polling component.
- Modify `frontend/app/pipeline/page.tsx`: render task control and recent tasks.
- Modify frontend tests for contracts, repositories, and HTTP data source.

## Task 1: Backend Task Model And Storage

**Files:**
- Modify: `app/models.py`
- Modify: `app/storage.py`
- Test: `tests/test_pipeline_tasks.py`

- [ ] **Step 1: Write failing storage tests**

Add `tests/test_pipeline_tasks.py`:

```python
from __future__ import annotations

from app.storage import Database


def test_pipeline_task_lifecycle_persists_status_result_and_error(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    task = db.create_pipeline_task(
        task_type="full_pipeline",
        requested_by="operator",
        parameters={"notify": True, "editorialLimit": 3},
    )

    assert task.task_id is not None
    assert task.status == "queued"
    assert task.current_stage == "queued"
    assert task.progress_current == 0
    assert task.progress_total == 3

    running = db.mark_pipeline_task_running(task.task_id, stage="crawl", progress_current=1)
    assert running.status == "running"
    assert running.started_at is not None
    assert running.current_stage == "crawl"

    db.update_pipeline_task_progress(
        task.task_id,
        stage="editorial",
        progress_current=2,
        result_patch={"crawl": {"totalFetched": 5, "totalNew": 2}},
    )
    finished = db.finish_pipeline_task(
        task.task_id,
        status="success",
        stage="done",
        result_patch={"editorial": {"generated": 6}},
    )

    assert finished.status == "success"
    assert finished.current_stage == "done"
    assert finished.progress_current == 3
    assert finished.finished_at is not None
    assert finished.result["crawl"]["totalFetched"] == 5
    assert finished.result["editorial"]["generated"] == 6


def test_pipeline_task_cancel_only_allows_queued_tasks(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    queued = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})

    cancelled = db.cancel_pipeline_task(queued.task_id)
    assert cancelled.status == "cancelled"
    assert cancelled.current_stage == "done"

    running = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})
    db.mark_pipeline_task_running(running.task_id, stage="crawl", progress_current=1)

    try:
        db.cancel_pipeline_task(running.task_id)
    except ValueError as exc:
        assert "only queued tasks can be cancelled" in str(exc)
    else:
        raise AssertionError("running task cancellation should fail")
```

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline_tasks.py -q
```

Expected: fails because `create_pipeline_task` and related storage methods do not exist.

- [ ] **Step 3: Add model and storage methods**

Implement:

- `PipelineTask` in `app/models.py`
- import it in `app/storage.py`
- storage methods:
  - `create_pipeline_task`
  - `get_pipeline_task`
  - `list_pipeline_tasks`
  - `mark_pipeline_task_running`
  - `update_pipeline_task_progress`
  - `finish_pipeline_task`
  - `cancel_pipeline_task`

Use JSON defaults as dictionaries, set `finished_at` on terminal statuses, and merge result patches by top-level key.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline_tasks.py -q
```

Expected: both tests pass.

## Task 2: Backend Runner

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/pipeline_tasks.py`
- Test: `tests/test_pipeline_tasks.py`

- [ ] **Step 1: Write failing runner tests**

Extend `tests/test_pipeline_tasks.py` with a synchronous runner test using injected callables:

```python
from app.tasks.pipeline_tasks import PipelineTaskRunner


class FakePipelineSummary:
    total_fetched = 5
    total_new = 2
    total_insighted = 5
    failed_sources = []
    has_failures = False
    per_source = {"arxiv": {"status": "success", "fetched": 5, "new": 2}}


class FakeEditorialResult:
    generated = 6
    outputs = []


class FakeNotificationSummary:
    attempted = 2
    succeeded = 2
    failed = 0


def test_pipeline_task_runner_executes_full_pipeline_and_records_results(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(
        task_type="full_pipeline",
        requested_by="operator",
        parameters={"notify": True, "editorialLimit": 3},
    )
    calls = []

    runner = PipelineTaskRunner(
        db=db,
        settings_factory=lambda: type("Settings", (), {"database_url": f"sqlite:///{tmp_path/'papers.db'}", "feishu_bot_webhook": "hook", "feishu_bot_secret": None, "max_notify_items": 10})(),
        source_factory=lambda: ["source"],
        pipeline_runner=lambda **kwargs: calls.append(("crawl", kwargs)) or FakePipelineSummary(),
        editorial_runner=lambda **kwargs: calls.append(("editorial", kwargs)) or FakeEditorialResult(),
        notification_runner=lambda **kwargs: calls.append(("notify", kwargs)) or FakeNotificationSummary(),
        notifier_factory=lambda settings: object(),
    )

    runner.run_task_once(task.task_id)

    stored = db.get_pipeline_task(task.task_id)
    assert stored.status == "success"
    assert stored.current_stage == "done"
    assert stored.result["crawl"]["totalFetched"] == 5
    assert stored.result["editorial"]["generated"] == 6
    assert stored.result["notify"]["succeeded"] == 2
    assert [name for name, _ in calls] == ["crawl", "editorial", "notify"]
```

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline_tasks.py::test_pipeline_task_runner_executes_full_pipeline_and_records_results -q
```

Expected: fails because `PipelineTaskRunner` does not exist.

- [ ] **Step 3: Implement runner**

Implement `PipelineTaskRunner` with:

- `enqueue(task_id)`
- `start()`
- `stop()`
- `run_task_once(task_id)` for deterministic tests
- default helpers for settings, sources, pipeline, editorial, notification, and notifier

The runner should mark task failed on exceptions and on pipeline summaries where `has_failures` is true.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline_tasks.py -q
```

Expected: all task tests pass.

## Task 3: Task API

**Files:**
- Modify: `app/api/schemas.py`
- Modify: `app/api/routes/pipeline.py`
- Modify: `app/api/app.py`
- Test: `tests/test_api_pipeline.py`

- [ ] **Step 1: Write failing API tests**

Add tests to `tests/test_api_pipeline.py`:

```python
def test_pipeline_tasks_api_creates_lists_gets_and_cancels_tasks(tmp_path):
    app = create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
    )
    client = ASGITestClient(app)

    create_response = client.post(
        "/pipeline/tasks",
        json={"taskType": "full_pipeline", "requestedBy": "operator", "notify": False, "editorialLimit": 2},
    )
    assert create_response.status_code == 200
    task = create_response.json()["data"]
    assert task["taskType"] == "full_pipeline"
    assert task["status"] == "queued"
    assert task["parameters"]["notify"] is False

    list_response = client.get("/pipeline/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1

    get_response = client.get(f"/pipeline/tasks/{task['taskId']}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["taskId"] == task["taskId"]

    cancel_response = client.post(f"/pipeline/tasks/{task['taskId']}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"
```

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_api_pipeline.py::test_pipeline_tasks_api_creates_lists_gets_and_cancels_tasks -q
```

Expected: fails because `/pipeline/tasks` does not exist and `create_app` does not accept `start_task_runner`.

- [ ] **Step 3: Add schemas, routes, and app runner wiring**

Add:

- `PipelineTaskCreateRequest`
- `PipelineTaskItem`
- `PipelineTasksResponse`

Update `create_app` signature:

```python
def create_app(*, database_url: str | None = None, editorial_root: Path | None = None, start_task_runner: bool = True) -> FastAPI:
```

Create runner and attach it to `app.state.pipeline_task_runner`. In tests, `start_task_runner=False` prevents background execution.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tests/test_api_pipeline.py tests/test_pipeline_tasks.py -q
```

Expected: relevant backend tests pass.

## Task 4: Frontend Contracts And Data Sources

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api-contracts.ts`
- Modify: `frontend/lib/data-sources/http/shared.ts`
- Modify: `frontend/lib/data-sources/http/pipeline.ts`
- Modify: `frontend/lib/data-sources/demo/pipeline.ts`
- Modify: `frontend/lib/repositories/pipeline.ts`
- Test: `frontend/tests/api-contracts.test.ts`
- Test: `frontend/tests/http-data-sources.test.ts`
- Test: `frontend/tests/repositories.test.ts`

- [ ] **Step 1: Write failing frontend data-source tests**

Add expectations for:

- task request/response types
- HTTP POST to `/pipeline/tasks`
- list/get/cancel repository methods

- [ ] **Step 2: Verify RED**

Run:

```bash
cd frontend
npm run test
```

Expected: fails because pipeline task methods and POST helper do not exist.

- [ ] **Step 3: Implement task types and methods**

Add `PipelineTaskItem`, `PipelineTaskCreateInput`, `PipelineTasksResponse`, and methods:

- `createPipelineTask(input)`
- `listPipelineTasks()`
- `getPipelineTask(taskId)`
- `cancelPipelineTask(taskId)`

Add `post<TData>(path, body?)` to the HTTP client.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd frontend
npm run test
```

Expected: frontend tests pass.

## Task 5: Frontend Task Control UI

**Files:**
- Create: `frontend/components/pipeline-task-control.tsx`
- Modify: `frontend/app/pipeline/page.tsx`
- Modify: `frontend/lib/queries.ts`

- [ ] **Step 1: Add query/action wrappers**

Expose:

- `getPipelineTasks()`
- `createPipelineTask(input)`
- `getPipelineTask(taskId)`
- `cancelPipelineTask(taskId)`

- [ ] **Step 2: Add client component**

Create a `PipelineTaskControl` client component with:

- notify toggle
- editorial limit numeric input
- start button
- recent task list
- polling for the most recently created running/queued task

- [ ] **Step 3: Render on pipeline page**

Load recent tasks on the server and render the control before run-history sections.

- [ ] **Step 4: Verify UI build**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: lint and production build pass.

## Task 6: Full Verification

**Files:**
- All touched files

- [ ] **Step 1: Run backend tests**

```bash
.venv/bin/python -m pytest tests/ -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend
npm run test
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run frontend lint and build**

```bash
cd frontend
npm run lint
npm run build
```

Expected: both pass.

- [ ] **Step 4: Manual API smoke test**

With backend running, call:

```bash
curl -s -X POST http://127.0.0.1:8000/pipeline/tasks \
  -H 'content-type: application/json' \
  -d '{"taskType":"full_pipeline","requestedBy":"manual","notify":false,"editorialLimit":1}'
```

Expected: JSON envelope with `status` `queued` or `running` and a numeric `taskId`.
