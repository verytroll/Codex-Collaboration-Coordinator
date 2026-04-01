"""Operator dashboard and debug routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_operator_dashboard_service
from app.models.api.operator_dashboard import OperatorDashboardResponse, OperatorDebugResponse
from app.services.operator_dashboard import (
    OperatorDashboardFilters,
    OperatorDashboardService,
)

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


def _filters(
    session_id: str | None = None,
    template_key: str | None = None,
    phase_key: str | None = None,
    runtime_pool_key: str | None = None,
) -> OperatorDashboardFilters:
    return OperatorDashboardFilters(
        session_id=session_id,
        template_key=template_key,
        phase_key=phase_key,
        runtime_pool_key=runtime_pool_key,
    )


@router.get("/dashboard", response_model=OperatorDashboardResponse)
async def get_operator_dashboard(
    dashboard_service: Annotated[OperatorDashboardService, Depends(get_operator_dashboard_service)],
    session_id: str | None = None,
    template_key: str | None = None,
    phase_key: str | None = None,
    runtime_pool_key: str | None = None,
) -> OperatorDashboardResponse:
    return OperatorDashboardResponse(
        **(
            await dashboard_service.get_dashboard(
                _filters(
                    session_id=session_id,
                    template_key=template_key,
                    phase_key=phase_key,
                    runtime_pool_key=runtime_pool_key,
                )
            )
        )
    )


@router.get("/debug", response_model=OperatorDebugResponse)
async def get_operator_debug(
    dashboard_service: Annotated[OperatorDashboardService, Depends(get_operator_dashboard_service)],
    session_id: str | None = None,
    template_key: str | None = None,
    phase_key: str | None = None,
    runtime_pool_key: str | None = None,
) -> OperatorDebugResponse:
    return OperatorDebugResponse(
        **(
            await dashboard_service.get_debug_surface(
                _filters(
                    session_id=session_id,
                    template_key=template_key,
                    phase_key=phase_key,
                    runtime_pool_key=runtime_pool_key,
                )
            )
        )
    )
