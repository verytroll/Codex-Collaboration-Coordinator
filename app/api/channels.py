"""Session channel API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_channel_service, get_session_repository
from app.models.api.channels import (
    ChannelCreateRequest,
    ChannelEnvelope,
    ChannelListEnvelope,
    ChannelResponse,
)
from app.repositories.channels import SessionChannelRecord
from app.repositories.sessions import SessionRepository
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/api/v1", tags=["channels"])


def _channel_response(record: SessionChannelRecord) -> ChannelResponse:
    return ChannelResponse(
        id=record.id,
        session_id=record.session_id,
        channel_key=record.channel_key,
        display_name=record.display_name,
        description=record.description,
        is_default=record.is_default,
        sort_order=record.sort_order,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _ensure_session_exists(
    session_repository: SessionRepository,
    session_id: str,
) -> None:
    session = await session_repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )


@router.get("/sessions/{session_id}/channels", response_model=ChannelListEnvelope)
async def list_channels(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
) -> ChannelListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    channels = await channel_service.list_channels(session_id)
    return ChannelListEnvelope(channels=[_channel_response(channel) for channel in channels])


@router.post(
    "/sessions/{session_id}/channels",
    response_model=ChannelEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    session_id: str,
    payload: ChannelCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
) -> ChannelEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    try:
        channel = await channel_service.create_channel(
            session_id=session_id,
            channel_key=payload.channel_key,
            display_name=payload.display_name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ChannelEnvelope(channel=_channel_response(channel))
