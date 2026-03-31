"""Agent API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_agent_repository,
    get_agent_runtime_repository,
    get_presence_repository,
)
from app.models.api.agents import (
    AgentCreateRequest,
    AgentEnvelope,
    AgentListEnvelope,
    AgentResponse,
    PresenceStatus,
    AgentUpdateRequest,
)
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.presence import PresenceHeartbeatRecord, PresenceRepository

router = APIRouter(prefix="/api/v1", tags=["agents"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_capabilities(role: str) -> dict[str, bool]:
    return {
        "can_code": role == "builder",
        "can_review": role == "reviewer",
        "can_plan": role == "planner",
    }


def _capabilities_from_record(record: AgentRecord) -> dict[str, bool]:
    if record.capabilities_json:
        try:
            data = json.loads(record.capabilities_json)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return {key: bool(value) for key, value in data.items()}
    return _default_capabilities(record.role)


def _presence_from_heartbeats(heartbeats: list[PresenceHeartbeatRecord]) -> str:
    if not heartbeats:
        return "unknown"
    latest = max(heartbeats, key=lambda heartbeat: (heartbeat.heartbeat_at, heartbeat.id))
    return latest.presence


def _latest_runtime(
    runtimes: list[AgentRuntimeRecord],
    agent_id: str,
) -> AgentRuntimeRecord | None:
    matching = [runtime for runtime in runtimes if runtime.agent_id == agent_id]
    if not matching:
        return None
    return max(matching, key=lambda runtime: (runtime.created_at, runtime.id))


def _agent_response(
    agent: AgentRecord,
    runtime: AgentRuntimeRecord | None,
    presence: str,
) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        display_name=agent.display_name,
        role=agent.role,
        is_lead=bool(agent.is_lead_default),
        runtime_kind=agent.runtime_kind,
        runtime_id=runtime.id if runtime else None,
        presence=cast(PresenceStatus, presence),
        capabilities=_capabilities_from_record(agent),
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


async def _build_agent_response(
    agent: AgentRecord,
    runtime_repository: AgentRuntimeRepository,
    presence_repository: PresenceRepository,
) -> AgentResponse:
    runtimes = await runtime_repository.list()
    runtime = _latest_runtime(runtimes, agent.id)
    heartbeats = await presence_repository.list_by_agent(agent.id)
    return _agent_response(agent, runtime, _presence_from_heartbeats(heartbeats))


async def _ensure_agent_exists(agent_repository: AgentRepository, agent_id: str) -> AgentRecord:
    agent = await agent_repository.get(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}",
        )
    return agent


@router.post("/agents", response_model=AgentEnvelope, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreateRequest,
    agent_repository: AgentRepository = Depends(get_agent_repository),
    runtime_repository: AgentRuntimeRepository = Depends(get_agent_runtime_repository),
) -> AgentEnvelope:
    created_at = _utc_now()
    agent_id = f"agt_{uuid4().hex}"
    runtime_id = f"rt_{payload.runtime_kind}_{agent_id}"
    capabilities_json = json.dumps(_default_capabilities(payload.role), sort_keys=True)
    default_config_json = (
        json.dumps(payload.runtime_config, sort_keys=True) if payload.runtime_config else None
    )
    agent = AgentRecord(
        id=agent_id,
        display_name=payload.display_name,
        role=payload.role,
        is_lead_default=int(payload.is_lead),
        runtime_kind=payload.runtime_kind,
        capabilities_json=capabilities_json,
        default_config_json=default_config_json,
        status="active",
        created_at=created_at,
        updated_at=created_at,
    )
    created_agent = await agent_repository.create(agent)
    runtime = AgentRuntimeRecord(
        id=runtime_id,
        agent_id=created_agent.id,
        runtime_kind=payload.runtime_kind,
        transport_kind="stdio",
        transport_config_json=default_config_json,
        workspace_path=(payload.runtime_config or {}).get("workspace_path"),
        approval_policy=(payload.runtime_config or {}).get("approval_policy"),
        sandbox_policy=(payload.runtime_config or {}).get("sandbox_mode"),
        runtime_status="starting",
        last_heartbeat_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    created_runtime = await runtime_repository.create(runtime)
    return AgentEnvelope(agent=_agent_response(created_agent, created_runtime, "unknown"))


@router.get("/agents", response_model=AgentListEnvelope)
async def list_agents(
    agent_repository: AgentRepository = Depends(get_agent_repository),
    runtime_repository: AgentRuntimeRepository = Depends(get_agent_runtime_repository),
    presence_repository: PresenceRepository = Depends(get_presence_repository),
) -> AgentListEnvelope:
    agents = await agent_repository.list()
    runtimes = await runtime_repository.list()
    heartbeats = await presence_repository.list()
    agent_responses = [
        _agent_response(
            agent,
            _latest_runtime(runtimes, agent.id),
            _presence_from_heartbeats(
                [heartbeat for heartbeat in heartbeats if heartbeat.agent_id == agent.id]
            ),
        )
        for agent in agents
    ]
    return AgentListEnvelope(agents=agent_responses)


@router.get("/agents/{agent_id}", response_model=AgentEnvelope)
async def get_agent(
    agent_id: str,
    agent_repository: AgentRepository = Depends(get_agent_repository),
    runtime_repository: AgentRuntimeRepository = Depends(get_agent_runtime_repository),
    presence_repository: PresenceRepository = Depends(get_presence_repository),
) -> AgentEnvelope:
    agent = await _ensure_agent_exists(agent_repository, agent_id)
    return AgentEnvelope(
        agent=await _build_agent_response(agent, runtime_repository, presence_repository)
    )


@router.patch("/agents/{agent_id}", response_model=AgentEnvelope)
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    agent_repository: AgentRepository = Depends(get_agent_repository),
    runtime_repository: AgentRuntimeRepository = Depends(get_agent_runtime_repository),
    presence_repository: PresenceRepository = Depends(get_presence_repository),
) -> AgentEnvelope:
    agent = await _ensure_agent_exists(agent_repository, agent_id)
    updated_role = payload.role if payload.role is not None else agent.role
    updated = AgentRecord(
        id=agent.id,
        display_name=payload.display_name if payload.display_name is not None else agent.display_name,
        role=updated_role,
        is_lead_default=(
            int(payload.is_lead) if payload.is_lead is not None else agent.is_lead_default
        ),
        runtime_kind=agent.runtime_kind,
        capabilities_json=json.dumps(_default_capabilities(updated_role), sort_keys=True),
        default_config_json=agent.default_config_json,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=_utc_now(),
    )
    saved = await agent_repository.update(updated)
    return AgentEnvelope(
        agent=await _build_agent_response(saved, runtime_repository, presence_repository)
    )
