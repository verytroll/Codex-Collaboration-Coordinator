"""Session API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_agent_repository,
    get_channel_service,
    get_session_repository,
)
from app.models.api.sessions import (
    SessionCreateRequest,
    SessionEnvelope,
    SessionListEnvelope,
    SessionResponse,
    SessionStatus,
    SessionUpdateRequest,
)
from app.repositories.agents import AgentRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/api/v1", tags=["sessions"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _session_response(record: SessionRecord) -> SessionResponse:
    return SessionResponse(
        id=record.id,
        title=record.title,
        goal=record.goal,
        status=cast(SessionStatus, record.status),
        lead_agent_id=record.lead_agent_id,
        active_phase_id=record.active_phase_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _ensure_agent_exists(
    agent_repository: AgentRepository,
    agent_id: str,
) -> None:
    if await agent_repository.get(agent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}",
        )


@router.post("/sessions", response_model=SessionEnvelope, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
) -> SessionEnvelope:
    if payload.lead_agent_id is not None:
        await _ensure_agent_exists(agent_repository, payload.lead_agent_id)

    created_at = _utc_now()
    session = SessionRecord(
        id=f"ses_{uuid4().hex}",
        title=payload.title,
        goal=payload.goal,
        status="active" if payload.lead_agent_id else "draft",
        lead_agent_id=payload.lead_agent_id,
        active_phase_id=None,
        loop_guard_status="normal",
        loop_guard_reason=None,
        last_message_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    created = await session_repository.create(session)
    await channel_service.ensure_default_channels(created.id)
    return SessionEnvelope(session=_session_response(created))


@router.get("/sessions", response_model=SessionListEnvelope)
async def list_sessions(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> SessionListEnvelope:
    sessions = await session_repository.list()
    return SessionListEnvelope(sessions=[_session_response(session) for session in sessions])


@router.get("/sessions/{session_id}", response_model=SessionEnvelope)
async def get_session(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> SessionEnvelope:
    session = await session_repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return SessionEnvelope(session=_session_response(session))


@router.patch("/sessions/{session_id}", response_model=SessionEnvelope)
async def update_session(
    session_id: str,
    payload: SessionUpdateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> SessionEnvelope:
    session = await session_repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    if payload.lead_agent_id is not None:
        await _ensure_agent_exists(agent_repository, payload.lead_agent_id)

    updated = SessionRecord(
        id=session.id,
        title=payload.title if payload.title is not None else session.title,
        goal=payload.goal if payload.goal is not None else session.goal,
        status=payload.status if payload.status is not None else session.status,
        lead_agent_id=(
            payload.lead_agent_id if payload.lead_agent_id is not None else session.lead_agent_id
        ),
        active_phase_id=(
            payload.active_phase_id
            if payload.active_phase_id is not None
            else session.active_phase_id
        ),
        loop_guard_status=session.loop_guard_status,
        loop_guard_reason=session.loop_guard_reason,
        last_message_at=session.last_message_at,
        created_at=session.created_at,
        updated_at=_utc_now(),
    )
    saved = await session_repository.update(updated)
    return SessionEnvelope(session=_session_response(saved))
