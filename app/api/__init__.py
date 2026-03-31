"""API layer package."""

from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router

router = APIRouter()
router.include_router(health_router)
router.include_router(sessions_router)
router.include_router(agents_router)

__all__ = ["router"]
