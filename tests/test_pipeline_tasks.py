from __future__ import annotations

import pytest

from app.schemas import PaperRecord
from app.storage import Database
from app.summarization.schemas import PaperInsightRecord
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


def test_pipeline_task_cancel_queued_transitions_to_cancelled(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    queued = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})

    cancelled = db.cancel_pipeline_task(queued.task_id)
    assert cancelled.status == "cancelled"
    assert cancelled.current_stage == "done"
    assert cancelled.finished_at is not None


def test_pipeline_task_cancel_running_transitions_to_cancelling(tmp_path):
    """Cancelling a running task signals the worker but does not finalize it.

    The worker is the only thing allowed to write the terminal ``cancelled``
    row + ``finished_at`` once it observes the signal at the next checkpoint.
    """
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})
    db.mark_pipeline_task_running(task.task_id, stage="crawl", progress_current=1)

    cancelling = db.cancel_pipeline_task(task.task_id)
    assert cancelling.status == "cancelling"
    # finished_at is still None — the worker hasn't observed the signal yet.
    assert cancelling.finished_at is None

    # Idempotent: cancelling a cancelling task does not raise.
    again = db.cancel_pipeline_task(task.task_id)
    assert again.status == "cancelling"

    assert db.is_cancellation_requested(task.task_id) is True


def test_pipeline_task_cancel_terminal_task_raises(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})
    db.mark_pipeline_task_running(task.task_id, stage="crawl", progress_current=1)
    db.finish_pipeline_task(task.task_id, status="success", stage="done")

    with pytest.raises(ValueError):
        db.cancel_pipeline_task(task.task_id)


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
    # Worker id is recorded so a future restart can identify orphans.
    assert stored.worker_id is not None and stored.worker_id == runner.worker_id


def _build_runner(
    db: Database,
    *,
    calls: list | None = None,
    worker_id: str | None = None,
    timeout_seconds: float = 1800,
    pipeline_runner=None,
    editorial_runner=None,
    notification_runner=None,
) -> PipelineTaskRunner:
    """Helper for tests: PipelineTaskRunner wired with no-op stage runners."""
    calls = calls if calls is not None else []
    return PipelineTaskRunner(
        db=db,
        settings_factory=lambda: type(
            "Settings",
            (),
            {
                "database_url": "sqlite:///:memory:",
                "feishu_bot_webhook": None,
                "feishu_bot_secret": None,
                "max_notify_items": 10,
                "pipeline_task_timeout_seconds": timeout_seconds,
            },
        )(),
        source_factory=lambda: [],
        pipeline_runner=pipeline_runner or (lambda **kwargs: calls.append(("crawl", kwargs)) or FakePipelineSummary()),
        editorial_runner=editorial_runner or (lambda **kwargs: calls.append(("editorial", kwargs)) or FakeEditorialResult()),
        notification_runner=notification_runner or (lambda **kwargs: calls.append(("notify", kwargs)) or FakeNotificationSummary()),
        notifier_factory=lambda settings: None,
        worker_id=worker_id,
    )


def test_runner_start_marks_orphaned_running_tasks_as_failed(tmp_path):
    """A previous process crashed mid-task; restart must not leave it stuck."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})
    db.mark_pipeline_task_running(task.task_id, stage="crawl", progress_current=1)
    assert db.get_pipeline_task(task.task_id).status == "running"

    runner = _build_runner(db)
    runner.start()
    try:
        recovered = db.get_pipeline_task(task.task_id)
        assert recovered.status == "failed"
        assert recovered.current_stage == "failed"
        assert recovered.error_message == "orphaned by process restart"
    finally:
        runner.stop()


def test_runner_start_re_enqueues_pending_queued_tasks(tmp_path):
    """The in-memory queue lives with the process; restart must restore it from DB."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(
        task_type="full_pipeline",
        requested_by="op",
        parameters={"notify": False, "editorialLimit": 1},
    )

    runner = _build_runner(db)
    runner.start()
    try:
        # The worker thread will eventually claim and process the task.
        # We don't sleep — instead poll for terminal status with a bound.
        import time
        deadline = time.time() + 3
        while time.time() < deadline:
            stored = db.get_pipeline_task(task.task_id)
            if stored.status in {"success", "failed"}:
                break
            time.sleep(0.05)
        stored = db.get_pipeline_task(task.task_id)
        assert stored.status == "success", f"expected success, got {stored.status} ({stored.error_message})"
    finally:
        runner.stop()


def test_claim_pipeline_task_is_atomic_across_competing_workers(tmp_path):
    """Two workers calling claim simultaneously: only one wins."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})

    first = db.claim_pipeline_task(task.task_id, worker_id="worker-A")
    second = db.claim_pipeline_task(task.task_id, worker_id="worker-B")

    assert first is True
    assert second is False
    stored = db.get_pipeline_task(task.task_id)
    assert stored.status == "running"
    assert stored.worker_id == "worker-A"


def test_run_task_once_silently_skips_when_another_worker_won_the_claim(tmp_path):
    """The losing worker must not raise — it just logs and moves on."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})

    # Worker A claims first
    assert db.claim_pipeline_task(task.task_id, worker_id="worker-A") is True

    # Worker B's run_task_once must not raise and must not change state
    runner_b = _build_runner(db, worker_id="worker-B")
    runner_b.run_task_once(task.task_id)

    stored = db.get_pipeline_task(task.task_id)
    assert stored.worker_id == "worker-A"
    assert stored.status == "running"  # still owned by A, not modified by B


def test_list_pipeline_tasks_by_status_filters_correctly(tmp_path):
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    queued1 = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})
    queued2 = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})
    running = db.create_pipeline_task(task_type="full_pipeline", requested_by="op", parameters={})
    db.mark_pipeline_task_running(running.task_id, stage="crawl", progress_current=1)

    queued_ids = {t.task_id for t in db.list_pipeline_tasks_by_status("queued")}
    running_ids = {t.task_id for t in db.list_pipeline_tasks_by_status("running")}

    assert queued_ids == {queued1.task_id, queued2.task_id}
    assert running_ids == {running.task_id}


def test_run_task_once_observes_cancellation_and_writes_cancelled(tmp_path):
    """User clicks cancel during the crawl stage; worker must abort cleanly.

    The worker checks for cancellation between stages, so once crawl returns
    we expect editorial / notify to be skipped and the task to land in the
    terminal ``cancelled`` state with ``finished_at`` set.
    """
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})

    cancel_after_crawl_state = {"cancelled": False}

    def cancel_during_crawl(**kwargs):
        # Simulate a user POSTing /pipeline/tasks/{id}/cancel mid-crawl.
        db.cancel_pipeline_task(task.task_id)
        cancel_after_crawl_state["cancelled"] = True
        return FakePipelineSummary()

    def must_not_run_editorial(**kwargs):
        raise AssertionError("editorial stage must not run after cancel")

    def must_not_run_notify(**kwargs):
        raise AssertionError("notify stage must not run after cancel")

    runner = _build_runner(
        db,
        pipeline_runner=cancel_during_crawl,
        editorial_runner=must_not_run_editorial,
        notification_runner=must_not_run_notify,
    )
    runner.run_task_once(task.task_id)

    assert cancel_after_crawl_state["cancelled"] is True
    stored = db.get_pipeline_task(task.task_id)
    assert stored.status == "cancelled"
    assert stored.current_stage == "done"
    assert stored.finished_at is not None
    assert stored.error_message and "cancel" in stored.error_message.lower()


def test_run_task_once_fails_with_timeout_when_elapsed_exceeds_limit(tmp_path):
    """A stage that runs longer than the configured budget must abort the task."""
    import time

    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()
    task = db.create_pipeline_task(task_type="full_pipeline", requested_by="operator", parameters={})

    def slow_crawl(**kwargs):
        # Sleep enough to blow past the 10ms test budget below.
        time.sleep(0.05)
        return FakePipelineSummary()

    def must_not_run_editorial(**kwargs):
        raise AssertionError("editorial stage was reached after deadline")

    def must_not_run_notify(**kwargs):
        raise AssertionError("notify stage was reached after deadline")

    runner = _build_runner(
        db,
        timeout_seconds=0.01,
        pipeline_runner=slow_crawl,
        editorial_runner=must_not_run_editorial,
        notification_runner=must_not_run_notify,
    )
    runner.run_task_once(task.task_id)

    stored = db.get_pipeline_task(task.task_id)
    assert stored.status == "failed"
    assert stored.current_stage == "failed"
    assert stored.error_message and "timeout" in stored.error_message.lower()
    assert stored.finished_at is not None


def _seed_paper_with_insight(db: Database, *, source_paper_id: str, title: str):
    paper = db.upsert_paper(
        PaperRecord(
            source="arxiv",
            source_paper_id=source_paper_id,
            title=title,
            abstract="abs",
            full_text="text",
            authors=["Alice"],
            paper_url=f"https://arxiv.org/abs/{source_paper_id}",
            dedup_key=f"{title.lower()}|alice|2026",
            raw_payload={"id": source_paper_id},
        )
    )
    db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="s",
            summary_long="l",
            novelty_points=["n"],
            limitations=[],
            applications=[],
            confidence_score=0.5,
        ),
    )
    return paper


def test_run_editorial_stage_skips_papers_that_already_have_a_draft(tmp_path, monkeypatch):
    """Re-triggering the dashboard pipeline must not regenerate drafts for
    papers that already have one — that would clobber reviewer/approver
    state via upsert_editorial_draft."""
    db = Database(f"sqlite:///{tmp_path/'papers.db'}")
    db.create_schema()

    drafted = _seed_paper_with_insight(db, source_paper_id="3000.0001", title="Drafted Paper")
    fresh = _seed_paper_with_insight(db, source_paper_id="3000.0002", title="Fresh Paper")

    db.upsert_editorial_draft(
        paper_id=drafted.paper_id,
        platform="bilibili",
        title="Existing",
        hook="hook",
        markdown_content="# existing\n",
        output_path=str(tmp_path / "outputs" / "bilibili-existing.md"),
    )

    captured: dict = {}

    def fake_generate_editorial_files(*, papers_with_insights, output_dir, db):
        captured["paper_ids"] = [p.paper_id for p, _ in papers_with_insights]
        return FakeEditorialResult()

    # Patch the symbol the runner imported — `from app.editorial.pipeline
    # import generate_editorial_files` binds it onto pipeline_tasks.
    import app.tasks.pipeline_tasks as pipeline_tasks_module

    monkeypatch.setattr(
        pipeline_tasks_module,
        "generate_editorial_files",
        fake_generate_editorial_files,
    )

    runner = _build_runner(db)
    result = runner._run_editorial_stage(
        db=db,
        settings=runner._settings_factory(),
        editorial_limit=10,
    )

    assert captured["paper_ids"] == [fresh.paper_id]
    assert getattr(result, "generated", 0) == FakeEditorialResult.generated
