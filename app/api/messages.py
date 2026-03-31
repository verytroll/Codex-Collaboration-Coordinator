"""Session message API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_agent_repository,
    get_message_mention_repository,
    get_message_repository,
    get_message_routing_service,
    get_participant_repository,
    get_session_event_repository,
    get_session_repository,
)
from app.models.api.messages import (
    MessageCreateEnvelope,
    MessageCreateRequest,
    MessageEnvelope,
    MessageListEnvelope,
    MessageResponse,
    MessageRoutingResponse,
    MessageSenderType,
    MessageType,
)
from app.repositories.agents import AgentRepository
from app.repositories.messages import MessageMentionRepository, MessageRecord, MessageRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.message_routing import MessageRoutingService
from app.services.session_events import record_session_event

router = APIRouter(prefix="/api/v1", tags=["messages"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _message_response(
    message: MessageRecord,
    mentions: list[str] | None = None,
) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        session_id=message.session_id,
        sender_type=cast(MessageSenderType, message.sender_type),
        sender_id=message.sender_id,
        content=message.content,
        message_type=cast(MessageType, message.message_type),
        reply_to_message_id=message.reply_to_message_id,
        mentions=mentions or [],
        artifacts=[],
        created_at=message.created_at,
    )


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


async def _ensure_agent_participant(
    participant_repository: ParticipantRepository,
    session_id: str,
    agent_id: str,
) -> None:
    participant = await participant_repository.get_by_session_and_agent(session_id, agent_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent {agent_id} is not a participant of session {session_id}",
        )


async def _ensure_reply_message(
    message_repository: MessageRepository,
    session_id: str,
    reply_to_message_id: str,
) -> None:
    reply_message = await message_repository.get(reply_to_message_id)
    if reply_message is None or reply_message.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reply message not found in session {session_id}: {reply_to_message_id}",
        )


def _apply_cursor_filter(
    messages: list[MessageRecord],
    cursor: str | None,
    *,
    is_before: bool,
) -> list[MessageRecord]:
    if cursor is None:
        return messages
    pivot_index = next(
        (index for index, message in enumerate(messages) if message.id == cursor), None
    )
    if pivot_index is not None:
        pivot_message = messages[pivot_index]
        pivot_key = (pivot_message.created_at, pivot_message.id)
    else:
        pivot_key = (cursor, "")
    filtered: list[MessageRecord] = []
    for message in messages:
        message_key = (message.created_at, message.id)
        if is_before and message_key < pivot_key:
            filtered.append(message)
        if not is_before and message_key > pivot_key:
            filtered.append(message)
    return filtered


async def _load_mentions(
    mention_repository: MessageMentionRepository,
    message_id: str,
) -> list[str]:
    mentions = await mention_repository.list_by_message(message_id)
    return [mention.mentioned_agent_id for mention in mentions]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageCreateEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_message(
    session_id: str,
    payload: MessageCreateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
    event_repository: Annotated[SessionEventRepository, Depends(get_session_event_repository)],
    routing_service: Annotated[MessageRoutingService, Depends(get_message_routing_service)],
) -> MessageCreateEnvelope:
    session = await _ensure_session_exists(session_repository, session_id)
    if payload.sender_type == "agent":
        if payload.sender_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sender_id is required when sender_type is agent",
            )
        sender_agent = await agent_repository.get(payload.sender_id)
        if sender_agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {payload.sender_id}",
            )
        await _ensure_agent_participant(participant_repository, session_id, payload.sender_id)
    elif payload.sender_type == "user" and payload.sender_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sender_id is required when sender_type is user",
        )
    if payload.reply_to_message_id is not None:
        await _ensure_reply_message(message_repository, session_id, payload.reply_to_message_id)

    try:
        routing_plan = await routing_service.preview(session_id=session_id, content=payload.content)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    created_at = _utc_now()
    message = MessageRecord(
        id=f"msg_{uuid4().hex}",
        session_id=session_id,
        sender_type=payload.sender_type,
        sender_id=payload.sender_id,
        message_type="command" if routing_plan.commands else payload.message_type,
        content=payload.content,
        content_format="plain_text",
        reply_to_message_id=payload.reply_to_message_id,
        source_message_id=None,
        visibility="session",
        created_at=created_at,
        updated_at=created_at,
    )
    created = await message_repository.create(message)
    session = SessionRecord(
        id=session.id,
        title=session.title,
        goal=session.goal,
        status=session.status,
        lead_agent_id=session.lead_agent_id,
        active_phase_id=session.active_phase_id,
        loop_guard_status=session.loop_guard_status,
        loop_guard_reason=session.loop_guard_reason,
        last_message_at=created_at,
        created_at=session.created_at,
        updated_at=created_at,
    )
    await session_repository.update(session)
    await record_session_event(
        event_repository,
        session_id=session_id,
        event_type="message.created",
        actor_type=payload.sender_type,
        actor_id=payload.sender_id,
        payload={
            "message_id": created.id,
            "sender_type": payload.sender_type,
            "sender_id": payload.sender_id,
        },
        created_at=created_at,
    )
    routing = await routing_service.apply(message=created, plan=routing_plan)
    mentions = await _load_mentions(mention_repository, created.id)
    return MessageCreateEnvelope(
        message=_message_response(created, mentions),
        routing=MessageRoutingResponse(
            detected_mentions=routing.detected_mentions,
            created_jobs=routing.created_jobs,
        ),
    )


@router.get("/sessions/{session_id}/messages", response_model=MessageListEnvelope)
async def list_messages(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    mention_repository: Annotated[
        MessageMentionRepository, Depends(get_message_mention_repository)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: str | None = None,
    after: str | None = None,
) -> MessageListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    messages = await message_repository.list_by_session(session_id)
    messages = _apply_cursor_filter(messages, after, is_before=False)
    messages = _apply_cursor_filter(messages, before, is_before=True)
    messages = messages[:limit]
    mentions_by_message_id: dict[str, list[str]] = {}
    for message in messages:
        mentions_by_message_id[message.id] = await _load_mentions(mention_repository, message.id)
    return MessageListEnvelope(
        messages=[
            _message_response(message, mentions_by_message_id.get(message.id))
            for message in messages
        ]
    )


@router.get("/messages/{message_id}", response_model=MessageEnvelope)
async def get_message(
    message_id: str,
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
) -> MessageEnvelope:
    message = await message_repository.get(message_id)
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message not found: {message_id}",
        )
    mentions = await _load_mentions(mention_repository, message.id)
    return MessageEnvelope(message=_message_response(message, mentions))
