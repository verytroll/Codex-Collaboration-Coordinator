"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
