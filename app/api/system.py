"""System status and diagnostics routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_debug_service, get_system_status_service
from app.core.config import get_config
from app.models.api.system import DebugSurfaceResponse, SystemStatusResponse
from app.services.debug_service import DebugService
from app.services.system_status import SystemStatusService

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    request: Request,
    system_status_service: Annotated[SystemStatusService, Depends(get_system_status_service)],
) -> SystemStatusResponse:
    payload = await system_status_service.get_status()
    config = get_config()
    return SystemStatusResponse(
        app={
            "name": request.app.title,
            "version": request.app.version,
            "env": config.app_env,
            "deployment_profile": config.deployment_profile,
        },
        **payload,
    )


@router.get("/debug", response_model=DebugSurfaceResponse)
async def get_debug_surface(
    debug_service: Annotated[DebugService, Depends(get_debug_service)],
) -> DebugSurfaceResponse:
    return DebugSurfaceResponse(**(await debug_service.get_surface()))
