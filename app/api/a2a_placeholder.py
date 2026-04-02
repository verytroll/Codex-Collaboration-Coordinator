"""A2A discovery placeholder routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.version import APP_VERSION
from app.models.api.system import (
    A2AAgentCardCapabilities,
    A2AAgentCardEndpointResponse,
    A2AAgentCardResponse,
    A2AAgentCardSkill,
)

router = APIRouter(tags=["a2a"])


def _agent_card(*, base_url: str) -> A2AAgentCardResponse:
    public_api_base_url = f"{base_url.rstrip('/')}/api/v1/a2a"
    return A2AAgentCardResponse(
        api_version="v1",
        contract_version="a2a.agent-card.v1",
        name="Codex Collaboration Coordinator",
        description=(
            "Local-first coordinator for multi-agent collaboration backed by CodexBridge and "
            "a public A2A task surface."
        ),
        version=APP_VERSION,
        public_api_base_url=public_api_base_url,
        capabilities=A2AAgentCardCapabilities(
            streaming=True,
            push_notifications=True,
            task_delegation=True,
            artifacts=True,
        ),
        endpoints=[
            A2AAgentCardEndpointResponse(
                name="discover",
                method="GET",
                path="/.well-known/agent-card.json",
                description="Return discovery metadata for A2A-aware clients.",
            ),
            A2AAgentCardEndpointResponse(
                name="create_task",
                method="POST",
                path="/api/v1/a2a/tasks",
                description="Project an internal job into the public A2A task surface.",
            ),
            A2AAgentCardEndpointResponse(
                name="list_tasks",
                method="GET",
                path="/api/v1/a2a/tasks",
                description="List public task projections, optionally scoped to a session.",
            ),
            A2AAgentCardEndpointResponse(
                name="get_task",
                method="GET",
                path="/api/v1/a2a/tasks/{task_id}",
                description="Fetch a public task projection by task id.",
            ),
            A2AAgentCardEndpointResponse(
                name="create_subscription",
                method="POST",
                path="/api/v1/a2a/tasks/{task_id}/subscriptions",
                description="Create a replay cursor for public task events.",
            ),
            A2AAgentCardEndpointResponse(
                name="list_task_events",
                method="GET",
                path="/api/v1/a2a/tasks/{task_id}/events",
                description="Replay public task events after a sequence cursor.",
            ),
            A2AAgentCardEndpointResponse(
                name="stream_task_events",
                method="GET",
                path="/api/v1/a2a/tasks/{task_id}/stream",
                description="Stream public task events as SSE frames with reconnect support.",
            ),
            A2AAgentCardEndpointResponse(
                name="stream_subscription_events",
                method="GET",
                path="/api/v1/a2a/subscriptions/{subscription_id}/events",
                description="Stream public task events as SSE frames.",
            ),
        ],
        skills=[
            A2AAgentCardSkill(
                id="collaboration",
                name="Collaboration",
                description=(
                    "Coordinate session-based work across planner, builder, and reviewer agents."
                ),
            ),
            A2AAgentCardSkill(
                id="codex-execution",
                name="Codex execution",
                description=(
                    "Relay work to CodexBridge and surface job updates, artifacts, and approvals."
                ),
            ),
            A2AAgentCardSkill(
                id="public-a2a",
                name="Public A2A interoperability",
                description=(
                    "Expose task projections, replayable events, and subscription streams for "
                    "external clients."
                ),
            ),
        ],
        compatibility_notes=[
            "Supported public v1 surface: task create/list/get, replay, "
            "subscriptions, and SSE streams.",
            "Legacy adapter bridge routes remain available for compatibility only.",
            "See docs/A2A_COMPATIBILITY_MATRIX.md for supported versus experimental claims.",
            "Replay cursors are inclusive by request and exclusive in storage.",
        ],
    )


@router.get("/.well-known/agent-card.json", response_model=A2AAgentCardResponse)
async def get_agent_card(request: Request) -> A2AAgentCardResponse:
    """Expose discovery metadata for A2A-compatible clients."""
    return _agent_card(base_url=str(request.base_url))
