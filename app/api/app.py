from __future__ import annotations

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


def create_app(*, database_url: str | None = None, editorial_root: Path | None = None) -> FastAPI:
    try:
        settings = AppSettings()
    except ValidationError:
        if DOTENV_PATH.exists():
            raise
        settings = None
    resolved_database_url = database_url or (settings.database_url if settings is not None else "sqlite:///:memory:")
    resolved_editorial_root = editorial_root or PROJECT_ROOT / "outputs" / "editorial"

    app = FastAPI(title="Paperclaw API")
    app.state.db = Database(resolved_database_url)
    app.state.db.create_schema()
    app.state.editorial_root = resolved_editorial_root
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
