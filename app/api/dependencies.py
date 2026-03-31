"""FastAPI dependencies for repository access."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import get_config
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.jobs import JobRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.presence import PresenceRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.job_service import JobService
from app.services.message_routing import MessageRoutingService
from app.services.runtime_service import RuntimeService


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


def get_runtime_service(
    runtime_repository: Annotated[AgentRuntimeRepository, Depends(get_agent_runtime_repository)],
) -> RuntimeService:
    """Provide a runtime service bound to the configured repositories."""
    return RuntimeService(runtime_repository)


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


def get_job_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> JobRepository:
    """Provide a job repository bound to the configured database."""
    return JobRepository(database_url)


def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
) -> JobService:
    """Provide a job service bound to the configured repositories."""
    return JobService(job_repository, runtime_service)


def get_message_routing_service(
    message_mention_repository: Annotated[
        MessageMentionRepository,
        Depends(get_message_mention_repository),
    ],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> MessageRoutingService:
    """Provide the message routing service."""
    return MessageRoutingService(
        message_mention_repository=message_mention_repository,
        participant_repository=participant_repository,
        agent_repository=agent_repository,
        job_service=job_service,
    )


def get_session_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionEventRepository:
    """Provide a session event repository bound to the configured database."""
    return SessionEventRepository(database_url)
