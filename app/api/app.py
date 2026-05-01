from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


_UNSET: object = object()


def create_app(
    *,
    database_url: str | None = None,
    editorial_root: Path | None = None,
    start_task_runner: bool = True,
    api_key: str | None | object = _UNSET,
    cors_allow_origins: list[str] | None = None,
) -> FastAPI:
    try:
        settings = AppSettings()
    except ValidationError:
        if DOTENV_PATH.exists():
            raise
        settings = None
    resolved_database_url = database_url or (settings.database_url if settings is not None else "sqlite:///:memory:")
    resolved_editorial_root = editorial_root or PROJECT_ROOT / "outputs" / "editorial"
    if api_key is _UNSET:
        resolved_api_key = settings.api_key if settings is not None else None
    else:
        resolved_api_key = api_key  # type: ignore[assignment]
    if cors_allow_origins is not None:
        resolved_cors_origins = cors_allow_origins
    elif settings is not None:
        resolved_cors_origins = settings.cors_allow_origins_list
    else:
        resolved_cors_origins = ["http://localhost:3000"]

    # Browsers reject ``Access-Control-Allow-Origin: *`` with credentialed
    # requests (cookies / Authorization headers). Since we set
    # ``allow_credentials=True`` below, accepting ``*`` here would ship a
    # configuration where every authenticated cross-origin request silently
    # fails in the browser. Fail fast at startup so the misconfiguration is
    # visible — operators should list explicit origins instead.
    if "*" in resolved_cors_origins:
        raise ValueError(
            "CORS configuration error: wildcard '*' is incompatible with "
            "allow_credentials=True (browsers reject credentialed requests "
            "to a wildcard origin). List explicit origins in "
            "CORS_ALLOW_ORIGINS instead."
        )

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    app.state.db = db
    app.state.editorial_root = resolved_editorial_root
    app.state.pipeline_task_runner = task_runner
    app.state.api_key = resolved_api_key
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
