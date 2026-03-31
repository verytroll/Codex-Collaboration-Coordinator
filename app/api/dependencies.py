"""FastAPI dependencies for repository access."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import get_config
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.presence import PresenceRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository


def get_database_url() -> str:
    """Return the active database URL from application config."""
    return get_config().database_url


def get_session_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionRepository:
    """Provide a session repository bound to the configured database."""
    return SessionRepository(database_url)


def get_agent_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> AgentRepository:
    """Provide an agent repository bound to the configured database."""
    return AgentRepository(database_url)


def get_agent_runtime_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> AgentRuntimeRepository:
    """Provide an agent runtime repository bound to the configured database."""
    return AgentRuntimeRepository(database_url)


def get_presence_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> PresenceRepository:
    """Provide a presence repository bound to the configured database."""
    return PresenceRepository(database_url)


def get_participant_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> ParticipantRepository:
    """Provide a participant repository bound to the configured database."""
    return ParticipantRepository(database_url)


def get_message_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> MessageRepository:
    """Provide a message repository bound to the configured database."""
    return MessageRepository(database_url)


def get_message_mention_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> MessageMentionRepository:
    """Provide a message mention repository bound to the configured database."""
    return MessageMentionRepository(database_url)


def get_session_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionEventRepository:
    """Provide a session event repository bound to the configured database."""
    return SessionEventRepository(database_url)
