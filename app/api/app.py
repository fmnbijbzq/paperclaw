from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import ValidationError

from app.api.routes.destinations import router as destinations_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.papers import router as papers_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.schemas import HealthResponse, create_envelope
from app.config import AppSettings, DOTENV_PATH, PROJECT_ROOT
from app.notifiers.feishu_bot import FeishuBotNotifier
from app.storage import Database
from app.tasks.pipeline_tasks import PipelineTaskRunner


def create_app(
    *,
    database_url: str | None = None,
    editorial_root: Path | None = None,
    start_task_runner: bool = True,
) -> FastAPI:
    try:
        settings = AppSettings()
    except ValidationError:
        if DOTENV_PATH.exists():
            raise
        settings = None
    resolved_database_url = database_url or (settings.database_url if settings is not None else "sqlite:///:memory:")
    resolved_editorial_root = editorial_root or PROJECT_ROOT / "outputs" / "editorial"

    db = Database(resolved_database_url)
    db.create_schema()
    task_runner = PipelineTaskRunner(db=db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_task_runner:
            task_runner.start()
        try:
            yield
        finally:
            task_runner.stop()

    app = FastAPI(title="Paperclaw API", lifespan=lifespan)
    app.state.db = db
    app.state.editorial_root = resolved_editorial_root
    app.state.pipeline_task_runner = task_runner
    app.state.notification_notifier = None
    if settings is not None and settings.feishu_bot_webhook:
        app.state.notification_notifier = FeishuBotNotifier(
            settings.feishu_bot_webhook,
            secret=settings.feishu_bot_secret,
            max_items=settings.max_notify_items,
        )

    @app.get("/health")
    async def health() -> dict:
        return create_envelope(HealthResponse(status="ok")).model_dump(by_alias=True)

    app.include_router(papers_router)
    app.include_router(drafts_router)
    app.include_router(destinations_router)
    app.include_router(notifications_router)
    app.include_router(pipeline_router)
    return app
