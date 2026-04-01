"""Thin operator UI shell routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_operator_shell_service
from app.core.config import get_config
from app.models.api.operator_ui import OperatorShellResponse
from app.services.operator_dashboard import OperatorDashboardFilters
from app.services.operator_shell import OperatorShellService

ui_router = APIRouter(prefix="/operator", tags=["operator-ui"])
shell_router = APIRouter(prefix="/api/v1/operator", tags=["operator-ui"])

_UI_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "ui" / "index.html"
_BOOTSTRAP_PATH = "/api/v1/operator/shell"


def _render_operator_shell_page() -> str:
    template = _UI_TEMPLATE_PATH.read_text(encoding="utf-8")
    config = get_config()
    rendered = template.replace("__BOOTSTRAP_PATH__", json.dumps(_BOOTSTRAP_PATH))
    rendered = rendered.replace(
        "__ACCESS_TOKEN__",
        json.dumps(config.access_token or ""),
    )
    rendered = rendered.replace(
        "__ACCESS_TOKEN_HEADER__",
        json.dumps(config.access_token_header),
    )
    return rendered


@ui_router.get("", response_class=HTMLResponse, include_in_schema=False)
async def get_operator_shell_page() -> HTMLResponse:
    """Render the thin operator shell page."""
    return HTMLResponse(_render_operator_shell_page())


@shell_router.get("/shell", response_model=OperatorShellResponse)
async def get_operator_shell(
    shell_service: Annotated[OperatorShellService, Depends(get_operator_shell_service)],
    session_id: str | None = None,
    template_key: str | None = None,
    phase_key: str | None = None,
    runtime_pool_key: str | None = None,
) -> OperatorShellResponse:
    """Return the shell bootstrap payload for the current operator view."""
    return await shell_service.get_shell(
        OperatorDashboardFilters(
            session_id=session_id,
            template_key=template_key,
            phase_key=phase_key,
            runtime_pool_key=runtime_pool_key,
        ),
        selected_session_id=session_id,
    )


__all__ = ["ui_router", "shell_router"]
