"""Health check routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_deployment_readiness_service
from app.core.config import get_config
from app.models.api.system import DeploymentReadinessResponse, HealthResponse
from app.services.deployment_readiness import DeploymentReadinessService

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


@router.get("/readinessz", response_model=DeploymentReadinessResponse)
async def readinessz(
    request: Request,
    response: Response,
    readiness_service: Annotated[
        DeploymentReadinessService,
        Depends(get_deployment_readiness_service),
    ],
) -> DeploymentReadinessResponse:
    payload = await readiness_service.get_readiness()
    config = get_config()
    readiness = DeploymentReadinessResponse(
        app={
            "name": request.app.title,
            "version": request.app.version,
            "env": config.app_env,
            "deployment_profile": config.deployment_profile,
        },
        **payload,
    )
    response.status_code = 200 if readiness.status == "ok" else 503
    return readiness
