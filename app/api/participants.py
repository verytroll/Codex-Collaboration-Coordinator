"""Session participant API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_agent_repository,
    get_agent_runtime_repository,
    get_participant_repository,
    get_session_event_repository,
    get_session_repository,
)
from app.models.api.participants import (
    ParticipantCreateRequest,
    ParticipantEnvelope,
    ParticipantListEnvelope,
    ParticipantResponse,
)
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.session_events import record_session_event

router = APIRouter(prefix="/api/v1", tags=["participants"])

DEFAULT_READ_SCOPE = "shared_history"
DEFAULT_WRITE_SCOPE = "mention_or_direct_assignment"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _participant_response(record: SessionParticipantRecord) -> ParticipantResponse:
    return ParticipantResponse(
        session_id=record.session_id,
        agent_id=record.agent_id,
        joined_at=record.joined_at or record.created_at,
        read_scope=record.read_scope,
        write_scope=record.write_scope,
    )


def _latest_runtime_id(runtimes: list[AgentRuntimeRecord], agent_id: str) -> str | None:
    matching = [runtime for runtime in runtimes if runtime.agent_id == agent_id]
    if not matching:
        return None
    latest_runtime = max(matching, key=lambda runtime: (runtime.created_at, runtime.id))
    return latest_runtime.id


async def _ensure_session_exists(
    session_repository: SessionRepository,
    session_id: str,
) -> SessionRecord:
    session = await session_repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return session


async def _ensure_agent_exists(
    agent_repository: AgentRepository,
    agent_id: str,
) -> AgentRecord:
    agent = await agent_repository.get(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}",
        )
    return agent


@router.post(
    "/sessions/{session_id}/participants",
    response_model=ParticipantEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_participant(
    session_id: str,
    payload: ParticipantCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    runtime_repository: Annotated[
        AgentRuntimeRepository,
        Depends(get_agent_runtime_repository),
    ],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    event_repository: Annotated[SessionEventRepository, Depends(get_session_event_repository)],
) -> ParticipantEnvelope:
    session = await _ensure_session_exists(session_repository, session_id)
    agent = await _ensure_agent_exists(agent_repository, payload.agent_id)
    existing = await participant_repository.get_by_session_and_agent(session_id, payload.agent_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Participant already exists for session {session_id} and agent {payload.agent_id}"
            ),
        )

    runtimes = await runtime_repository.list()
    runtime_id = _latest_runtime_id(runtimes, agent.id)

    created_at = _utc_now()
    participant = SessionParticipantRecord(
        id=f"sp_{uuid4().hex}",
        session_id=session_id,
        agent_id=agent.id,
        runtime_id=runtime_id,
        is_lead=1 if session.lead_agent_id == agent.id or agent.is_lead_default else 0,
        read_scope=DEFAULT_READ_SCOPE,
        write_scope=DEFAULT_WRITE_SCOPE,
        participant_status="joined",
        joined_at=created_at,
        left_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    created = await participant_repository.create(participant)
    await record_session_event(
        event_repository,
        session_id=session_id,
        event_type="participant.added",
        actor_type="agent",
        actor_id=agent.id,
        payload={"agent_id": agent.id, "participant_id": created.id},
        created_at=created_at,
    )
    return ParticipantEnvelope(participant=_participant_response(created))


@router.get("/sessions/{session_id}/participants", response_model=ParticipantListEnvelope)
async def list_participants(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
) -> ParticipantListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    participants = await participant_repository.list_by_session(session_id)
    return ParticipantListEnvelope(
        participants=[_participant_response(participant) for participant in participants]
    )


@router.delete(
    "/sessions/{session_id}/participants/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_participant(
    session_id: str,
    agent_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    event_repository: Annotated[SessionEventRepository, Depends(get_session_event_repository)],
) -> None:
    await _ensure_session_exists(session_repository, session_id)
    participant = await participant_repository.get_by_session_and_agent(session_id, agent_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant not found in session {session_id}: {agent_id}",
        )
    deleted = await participant_repository.delete(participant.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant not found: {participant.id}",
        )
    await record_session_event(
        event_repository,
        session_id=session_id,
        event_type="participant.removed",
        actor_type="system",
        actor_id="api",
        payload={"agent_id": agent_id, "participant_id": participant.id},
    )
