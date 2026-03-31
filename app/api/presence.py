"""Presence API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_agent_repository,
    get_presence_repository,
    get_presence_service,
)
from app.models.api.agents import PresenceStatus
from app.models.api.presence import (
    PresenceEnvelope,
    PresenceHeartbeatRequest,
    PresenceHeartbeatResponse,
)
from app.repositories.agents import AgentRepository
from app.repositories.presence import PresenceRepository
from app.services.presence import PresenceService, PresenceSnapshot

router = APIRouter(prefix="/api/v1", tags=["presence"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _heartbeat_response(
    *,
    agent_id: str,
    id: str,
    runtime_id: str | None,
    presence: str,
    heartbeat_at: str,
    created_at: str,
    details: dict[str, object] | None = None,
) -> PresenceHeartbeatResponse:
    return PresenceHeartbeatResponse(
        id=id,
        agent_id=agent_id,
        runtime_id=runtime_id,
        presence=presence,
        heartbeat_at=heartbeat_at,
        details=details,
        created_at=created_at,
    )


def _from_snapshot(agent_id: str, snapshot: PresenceSnapshot) -> PresenceHeartbeatResponse:
    heartbeat_at = snapshot.heartbeat_at or _utc_now()
    return _heartbeat_response(
        agent_id=agent_id,
        id=f"presence_{agent_id}",
        runtime_id=snapshot.runtime_id,
        presence=cast(PresenceStatus, snapshot.presence),
        heartbeat_at=heartbeat_at,
        created_at=heartbeat_at,
    )


async def _ensure_agent(
    agent_repository: AgentRepository,
    agent_id: str,
) -> None:
    agent = await agent_repository.get(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}",
        )


@router.post("/agents/{agent_id}/heartbeat", response_model=PresenceEnvelope, status_code=201)
async def post_heartbeat(
    agent_id: str,
    payload: PresenceHeartbeatRequest,
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    presence_service: Annotated[PresenceService, Depends(get_presence_service)],
) -> PresenceEnvelope:
    await _ensure_agent(agent_repository, agent_id)
    heartbeat = await presence_service.record_heartbeat(
        agent_id=agent_id,
        runtime_id=payload.runtime_id,
        presence=payload.presence,
        details=payload.details,
        heartbeat_at=payload.heartbeat_at,
    )
    return PresenceEnvelope(
        presence=_heartbeat_response(
            agent_id=heartbeat.agent_id,
            id=heartbeat.id,
            runtime_id=heartbeat.runtime_id,
            presence=heartbeat.presence,
            heartbeat_at=heartbeat.heartbeat_at,
            created_at=heartbeat.created_at,
            details=(payload.details if payload.details is not None else None),
        )
    )


@router.get("/agents/{agent_id}/presence", response_model=PresenceEnvelope)
async def get_presence(
    agent_id: str,
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    presence_repository: Annotated[PresenceRepository, Depends(get_presence_repository)],
    presence_service: Annotated[PresenceService, Depends(get_presence_service)],
) -> PresenceEnvelope:
    await _ensure_agent(agent_repository, agent_id)
    heartbeats = await presence_repository.list_by_agent(agent_id)
    if heartbeats:
        latest = max(heartbeats, key=lambda heartbeat: (heartbeat.heartbeat_at, heartbeat.id))
        return PresenceEnvelope(
            presence=_heartbeat_response(
                agent_id=latest.agent_id,
                id=latest.id,
                runtime_id=latest.runtime_id,
                presence=latest.presence,
                heartbeat_at=latest.heartbeat_at,
                created_at=latest.created_at,
                details=None,
            )
        )

    snapshot = await presence_service.get_snapshot(agent_id)
    return PresenceEnvelope(presence=_from_snapshot(agent_id, snapshot))
