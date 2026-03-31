"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api.system import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()
