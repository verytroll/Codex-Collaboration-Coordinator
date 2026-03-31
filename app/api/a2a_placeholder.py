"""A2A discovery placeholder routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api.system import (
    A2AAgentCardCapabilities,
    A2AAgentCardResponse,
    A2AAgentCardSkill,
)

router = APIRouter(tags=["a2a"])


def _agent_card() -> A2AAgentCardResponse:
    return A2AAgentCardResponse(
        name="Codex Collaboration Coordinator",
        description=(
            "Local-first coordinator for multi-agent collaboration backed by CodexBridge."
        ),
        version="0.1.0",
        capabilities=A2AAgentCardCapabilities(
            streaming=True,
            push_notifications=False,
            task_delegation=True,
            artifacts=True,
        ),
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
        ],
    )


@router.get("/.well-known/agent-card.json", response_model=A2AAgentCardResponse)
async def get_agent_card() -> A2AAgentCardResponse:
    """Expose a discovery placeholder for future A2A-compatible clients."""
    return _agent_card()
