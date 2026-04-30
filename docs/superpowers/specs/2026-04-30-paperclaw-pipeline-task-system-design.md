# Paperclaw Pipeline Task System Design

## Goal

Paperclaw currently depends on command-line scripts and cron for paper ingestion. The dashboard can display pipeline state and run history, but it cannot actively trigger a full paper workflow.

This design adds a durable task system that lets an operator trigger and observe the pipeline from the API and frontend. The first version covers:

- Crawl, normalize, store, and insight generation
- Editorial draft generation
- Optional Feishu notification

Export remains a separate human-driven workflow. The existing approval requirement for exports stays intact.

## Chosen Approach

Use a database-backed task model plus a single in-process FastAPI worker thread.

This matches the current project shape: single-host deployment, SQLite storage, script-oriented pipeline code, and a dashboard that already reads from the FastAPI service. It avoids adding Redis or an external worker dependency before the project needs distributed execution.

Alternative approaches considered:

- Synchronous API wrapper: simpler, but long requests can time out and cannot show progress.
- Celery/RQ/Redis: more scalable, but adds deployment and operational complexity that is not justified for the current single-server project.

## Task Model

Add a `PipelineTask` SQLAlchemy model and database table.

Fields:

- `task_id`: integer primary key
- `task_type`: first version supports `full_pipeline`
- `status`: `queued`, `running`, `success`, `failed`, or `cancelled`
- `current_stage`: `queued`, `crawl`, `editorial`, `notify`, `done`, or `failed`
- `progress_current`: integer
- `progress_total`: integer
- `requested_by`: operator label
- `parameters`: JSON payload such as `notify` and `editorialLimit`
- `result`: JSON stage summaries
- `error_message`: failure details when applicable
- `created_at`, `started_at`, `finished_at`

The model is intentionally generic enough to support future task types, but the first implementation only accepts `full_pipeline`.

## API

Add `/pipeline/tasks` endpoints to the existing pipeline router.

### Create Task

`POST /pipeline/tasks`

Request:

```json
{
  "taskType": "full_pipeline",
  "requestedBy": "operator",
  "notify": true,
  "editorialLimit": 3
}
```

Behavior:

- Persist a queued task.
- Enqueue it in the in-process runner.
- Return the task envelope immediately.

### List Tasks

`GET /pipeline/tasks?limit=50`

Returns recent tasks ordered newest first.

### Get Task

`GET /pipeline/tasks/{taskId}`

Returns one task, including current status, current stage, progress, result, and error.

### Cancel Task

`POST /pipeline/tasks/{taskId}/cancel`

First version only cancels queued tasks. Running tasks are not force-stopped because the current crawl, summary, editorial, and notification code does not expose safe cancellation points.

## Runner

Add `app/tasks/pipeline_tasks.py`.

The runner:

- Starts with the FastAPI app and is stored at `app.state.pipeline_task_runner`.
- Uses `queue.Queue` and one daemon worker thread.
- Executes one task at a time to avoid duplicate crawls and SQLite lock contention.
- Persists status transitions before and after each stage.

Execution stages:

1. `crawl`
   - Load `AppSettings` and `config/sources.yaml`.
   - Build enabled sources using the same logic as `run_once.py`.
   - Call `run_pipeline(...)`.
   - Store totals and per-source results in `PipelineTask.result`.

2. `editorial`
   - Load papers with insights using `Database.list_papers_with_insights(limit=editorialLimit)`.
   - Call `generate_editorial_files(...)`.
   - Store generated draft count and output paths.
   - If no papers with insights exist, record `generated=0` and continue.

3. `notify`
   - Runs only when the request has `notify=true`.
   - If Feishu is configured, call `run_notification_cycle(...)`.
   - If Feishu is not configured, skip notification and record a skipped result.

4. `done`
   - Mark the task `success` if all required stages completed.

If `run_pipeline` reports failed sources through `has_failures`, the task records the partial result and marks itself `failed`. It does not hide successfully stored papers.

## Frontend

Extend the pipeline dashboard with a task control area.

Controls:

- Start full pipeline
- Toggle Feishu notification
- Set editorial draft limit

Task display:

- Task ID
- Status
- Current stage
- Progress
- Requested by
- Start and finish times
- Error message
- Stage result summary

The first version should use a client polling component rather than WebSockets. Polling every three to five seconds is enough for the current operational use case and keeps the architecture simple.

## Data Source Integration

Extend the frontend pipeline data source and repository contracts:

- `createPipelineTask(input)`
- `listPipelineTasks()`
- `getPipelineTask(taskId)`
- `cancelPipelineTask(taskId)`

HTTP mode calls the new FastAPI endpoints. Demo mode can return fixture tasks and simulate creation without affecting backend state.

## Error Handling

Expected behavior:

- Invalid task type returns `400`.
- Missing task returns `404`.
- Cancelling a running task returns `409`.
- Notifier missing while `notify=true` does not fail the task; it records notification as skipped.
- Editorial stage with no insight-ready papers records zero generated drafts and continues.
- Source failures from crawl mark the task failed, while preserving per-source detail.
- Unexpected exceptions mark the task failed and persist `error_message`.

## Concurrency

The first version uses single-worker FIFO execution.

Reasons:

- Prevents overlapping crawls against the same SQLite database.
- Avoids duplicate external requests to arXiv, OpenReview, and CVF.
- Makes task history easy to reason about.

Queued tasks can be cancelled before the worker starts them. Running cancellation can be added later by inserting explicit cancellation checks between pipeline stages and, eventually, inside long-running source fetchers.

## Testing

Backend tests:

- Storage lifecycle for `PipelineTask`.
- Task creation persists `queued`.
- Runner transitions `queued -> running -> success`.
- Runner records crawl, editorial, and notification result JSON.
- Source failure marks the task failed with partial result.
- Queued task cancellation works.
- Running task cancellation is rejected.
- API endpoints create, list, get, and cancel tasks using response envelopes.

Frontend tests:

- API contract types cover pipeline task request and response payloads.
- HTTP data source sends `POST /pipeline/tasks` and parses task responses.
- Pipeline repository exposes task creation/list/get/cancel.
- Demo data source supplies stable task fixtures.

## Non-Goals

This first version does not:

- Add Redis, Celery, RQ, or distributed workers.
- Auto-approve or auto-export editorial drafts.
- Force-stop running tasks.
- Provide WebSocket progress streaming.
- Split `run_pipeline` into fine-grained per-paper progress callbacks.

## Migration Path

If Paperclaw later needs distributed workers, the database task model and API can remain stable. The in-process runner can be replaced by a Redis-backed worker while preserving the frontend contract and task history shape.
