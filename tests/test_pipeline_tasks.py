from __future__ import annotations

from app.storage import Database
from app.tasks.pipeline_tasks import PipelineTaskRunner


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
        settings_factory=lambda: type(
            "Settings",
            (),
            {
                "database_url": f"sqlite:///{tmp_path/'papers.db'}",
                "feishu_bot_webhook": "hook",
                "feishu_bot_secret": None,
                "max_notify_items": 10,
            },
        )(),
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
