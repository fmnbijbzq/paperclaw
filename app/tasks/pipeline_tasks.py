from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic
from typing import Any, Callable
from uuid import uuid4
import logging
import os
import socket

from app.config import AppSettings, PROJECT_ROOT, load_source_config
from app.editorial.pipeline import generate_editorial_files
from app.notification_pipeline import run_notification_cycle
from app.notifiers.feishu_bot import FeishuBotNotifier
from app.pipeline import run_pipeline
from app.publish.exporter import default_output_dir
from app.sources.arxiv import ArxivSource
from app.sources.cvf import CVFSource
from app.sources.openreview import OpenReviewSource
from app.storage import Database

LOGGER = logging.getLogger(__name__)
SOURCE_CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"

SettingsFactory = Callable[[], Any]
SourceFactory = Callable[[], list[Any]]
PipelineRunner = Callable[..., Any]
EditorialRunner = Callable[..., Any]
NotificationRunner = Callable[..., Any]
NotifierFactory = Callable[[Any], Any]


class _TaskCancelled(Exception):
    """Raised by the cancellation/timeout checkpoint when the user has cancelled the task."""


class _TaskTimeout(Exception):
    """Raised by the cancellation/timeout checkpoint when the task has exceeded its budget."""


def build_sources_from_config(path: Path = SOURCE_CONFIG_PATH) -> list[Any]:
    source_config = load_source_config(path)
    sources: list[Any] = []

    arxiv_config = source_config.get("arxiv", {})
    if arxiv_config.get("enabled"):
        sources.append(
            ArxivSource(
                allowed_categories=arxiv_config.get("categories"),
                lookback_days=arxiv_config.get("lookback_days"),
            )
        )

    openreview_config = source_config.get("openreview", {})
    if openreview_config.get("enabled"):
        sources.append(
            OpenReviewSource(
                venues=openreview_config.get("venues"),
                lookback_days=openreview_config.get("lookback_days"),
            )
        )

    cvf_config = source_config.get("cvf", {})
    if cvf_config.get("enabled"):
        sources.append(
            CVFSource(
                conferences=cvf_config.get("conferences"),
                lookback_days=cvf_config.get("lookback_days"),
                year=cvf_config.get("year"),
                max_results=cvf_config.get("max_results", 100),
            )
        )

    return sources


def build_feishu_notifier(settings: Any) -> FeishuBotNotifier | None:
    webhook = getattr(settings, "feishu_bot_webhook", None)
    if not webhook:
        return None
    return FeishuBotNotifier(
        webhook,
        secret=getattr(settings, "feishu_bot_secret", None),
        max_items=getattr(settings, "max_notify_items", 10),
    )


class PipelineTaskRunner:
    def __init__(
        self,
        *,
        db: Database,
        settings_factory: SettingsFactory = AppSettings,
        source_factory: SourceFactory = build_sources_from_config,
        pipeline_runner: PipelineRunner = run_pipeline,
        editorial_runner: EditorialRunner | None = None,
        notification_runner: NotificationRunner = run_notification_cycle,
        notifier_factory: NotifierFactory = build_feishu_notifier,
        worker_id: str | None = None,
    ) -> None:
        self._db = db
        self._settings_factory = settings_factory
        self._source_factory = source_factory
        self._pipeline_runner = pipeline_runner
        self._editorial_runner = editorial_runner or self._run_editorial_stage
        self._notification_runner = notification_runner
        self._notifier_factory = notifier_factory
        self._queue: Queue[int] = Queue()
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._worker_id = worker_id or self._build_default_worker_id()

    @staticmethod
    def _build_default_worker_id() -> str:
        return f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:8]}"

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def enqueue(self, task_id: int) -> None:
        self._queue.put(task_id)

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        # Recover from a previous process crash before accepting new work:
        #   * orphaned ``running`` tasks → mark failed (their worker is gone)
        #   * surviving ``queued`` tasks → re-enqueue (in-memory queue is empty
        #     because it lives in the dead process)
        self._reclaim_orphaned_running()
        self._enqueue_pending_queued()
        self._stop_event.clear()
        self._worker = Thread(target=self._work_loop, name="paperclaw-pipeline-task-runner", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=2)

    def _reclaim_orphaned_running(self) -> None:
        for task in self._db.list_pipeline_tasks_by_status("running"):
            LOGGER.warning(
                "pipeline task %s was stuck in 'running' on startup (worker=%s); marking failed",
                task.task_id,
                task.worker_id,
            )
            self._db.finish_pipeline_task(
                task.task_id,
                status="failed",
                stage="failed",
                error_message="orphaned by process restart",
            )

    def _enqueue_pending_queued(self) -> None:
        for task in self._db.list_pipeline_tasks_by_status("queued"):
            self._queue.put(task.task_id)

    def run_task_once(self, task_id: int) -> None:
        task = self._db.get_pipeline_task(task_id)
        if task is None:
            raise ValueError(f"pipeline task {task_id} does not exist")
        if task.status == "cancelled":
            return
        if task.status != "queued":
            # Either claimed by another worker or already finished — skip silently.
            return
        if not self._db.claim_pipeline_task(task_id, worker_id=self._worker_id):
            # Lost the race to another worker; nothing to do.
            return

        settings = self._settings_factory()
        parameters = dict(task.parameters or {})
        timeout_seconds = float(getattr(settings, "pipeline_task_timeout_seconds", 1800))
        deadline = monotonic() + timeout_seconds

        try:
            # Checkpoint right after claim — covers the case where the user
            # cancelled in the small window between create and claim.
            self._checkpoint(task_id, deadline)

            sources = self._source_factory()
            crawl_summary = self._pipeline_runner(
                database_url=settings.database_url,
                sources=sources,
                notifier=None,
            )
            self._checkpoint(task_id, deadline)
            crawl_result = self._crawl_result(crawl_summary)
            self._db.update_pipeline_task_progress(
                task_id,
                stage="editorial",
                progress_current=2,
                result_patch={"crawl": crawl_result},
            )
            if getattr(crawl_summary, "has_failures", False):
                failed_sources = ", ".join(getattr(crawl_summary, "failed_sources", []))
                self._db.finish_pipeline_task(
                    task_id,
                    status="failed",
                    stage="failed",
                    error_message=f"source failures: {failed_sources}",
                )
                return

            editorial_limit = int(parameters.get("editorialLimit") or 3)
            editorial_result = self._editorial_runner(
                db=self._db,
                settings=settings,
                editorial_limit=editorial_limit,
            )
            self._checkpoint(task_id, deadline)
            self._db.update_pipeline_task_progress(
                task_id,
                stage="notify",
                progress_current=3,
                result_patch={"editorial": self._editorial_result(editorial_result)},
            )

            notify_requested = bool(parameters.get("notify", True))
            notify_result = self._run_notify_stage(settings=settings) if notify_requested else {"skipped": "not requested"}
            self._db.finish_pipeline_task(
                task_id,
                status="success",
                stage="done",
                result_patch={"notify": notify_result},
            )
        except _TaskCancelled:
            # User-initiated cancel observed at a checkpoint. Worker is the
            # one that writes the terminal cancelled row + finished_at —
            # cancel_pipeline_task only flipped the running → cancelling flag.
            LOGGER.info("pipeline task %s cancelled by user", task_id)
            self._db.finish_pipeline_task(
                task_id,
                status="cancelled",
                stage="done",
                error_message="cancelled by user request",
            )
        except _TaskTimeout:
            LOGGER.warning(
                "pipeline task %s exceeded %.1fs timeout; aborting",
                task_id,
                timeout_seconds,
            )
            self._db.finish_pipeline_task(
                task_id,
                status="failed",
                stage="failed",
                error_message=f"timeout after {timeout_seconds:g}s",
            )
        except Exception as exc:
            LOGGER.exception("pipeline task %s failed", task_id)
            self._db.finish_pipeline_task(
                task_id,
                status="failed",
                stage="failed",
                error_message=str(exc),
            )

    def _checkpoint(self, task_id: int, deadline: float) -> None:
        """Bail out between stages if the user cancelled or we ran out of time.

        Cooperative cancellation: we cannot interrupt a stage that is already
        executing (e.g. an in-flight HTTP fetch), but we can prevent the next
        stage from starting and finalize the task quickly.
        """
        if self._db.is_cancellation_requested(task_id):
            raise _TaskCancelled()
        if monotonic() >= deadline:
            raise _TaskTimeout()

    def _work_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                task_id = self._queue.get(timeout=0.2)
            except Empty:
                continue
            try:
                self.run_task_once(task_id)
            finally:
                self._queue.task_done()

    def _run_editorial_stage(self, *, db: Database, settings: Any, editorial_limit: int) -> Any:
        del settings
        # ``where_no_draft=True`` makes re-triggering the dashboard pipeline
        # idempotent: papers that already have any EditorialDraft row are
        # skipped, so we never re-call upsert_editorial_draft on them (which
        # would reset status to ``generated`` and wipe reviewer/approver
        # fields). Newly crawled papers always get a draft on the next run.
        rows = db.list_papers_with_insights(limit=editorial_limit, where_no_draft=True)
        if not rows:
            return {"generated": 0, "outputs": [], "skipped": "no papers with insights"}
        return generate_editorial_files(
            papers_with_insights=rows,
            output_dir=default_output_dir(PROJECT_ROOT),
            db=db,
        )

    def _run_notify_stage(self, *, settings: Any) -> dict[str, Any]:
        notifier = self._notifier_factory(settings)
        if notifier is None:
            return {"skipped": "notifier not configured"}
        summary = self._notification_runner(
            database_url=settings.database_url,
            notifier=notifier,
            batch_size=getattr(settings, "max_notify_items", 10),
            destination="feishu",
        )
        return {
            "attempted": getattr(summary, "attempted", 0),
            "succeeded": getattr(summary, "succeeded", 0),
            "failed": getattr(summary, "failed", 0),
        }

    def _crawl_result(self, summary: Any) -> dict[str, Any]:
        return {
            "totalFetched": getattr(summary, "total_fetched", 0),
            "totalNew": getattr(summary, "total_new", 0),
            "totalInsighted": getattr(summary, "total_insighted", 0),
            "failedSources": list(getattr(summary, "failed_sources", [])),
            "perSource": dict(getattr(summary, "per_source", {})),
        }

    def _editorial_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        return {
            "generated": getattr(result, "generated", 0),
            "outputs": [str(path) for path in getattr(result, "outputs", [])],
        }
