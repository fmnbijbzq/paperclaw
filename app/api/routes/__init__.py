from app.api.routes.destinations import router as destinations_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.papers import router as papers_router

__all__ = ["papers_router", "drafts_router", "destinations_router"]
