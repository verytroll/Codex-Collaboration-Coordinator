"""FastAPI dependencies for repository access."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.codex_bridge import CodexProcessManager, JsonRpcClient
from app.core.config import get_config
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.jobs import JobEventRepository, JobRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.presence import PresenceRepository
from app.repositories.relay_edges import RelayEdgeRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.command_handler import CommandHandler
from app.services.job_service import JobService
from app.services.message_routing import MessageRoutingService
from app.services.permissions import CommandPermissions
from app.services.relay_engine import RelayEngine
from app.services.runtime_service import RuntimeService
from app.services.thread_mapping import ThreadMappingService, ThreadMappingStore

_THREAD_MAPPING_STORE = ThreadMappingStore()


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


def get_job_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> JobEventRepository:
    """Provide a job event repository bound to the configured database."""
    return JobEventRepository(database_url)


def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
) -> JobService:
    """Provide a job service bound to the configured repositories."""
    return JobService(job_repository, runtime_service)


def get_thread_mapping_service(
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
) -> ThreadMappingService:
    """Provide the session-thread mapping service."""
    return ThreadMappingService(runtime_service, store=_THREAD_MAPPING_STORE)


async def get_codex_bridge_client() -> AsyncIterator[JsonRpcClient]:
    """Provide a Codex JSON-RPC client for the current request."""
    manager = CodexProcessManager()
    process = await manager.start()
    client = JsonRpcClient(process)
    try:
        await client.initialize({"transport": "stdio"})
        yield client
    finally:
        await client.aclose()
        await manager.stop()


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


def get_command_permissions(
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
) -> CommandPermissions:
    """Provide command permission checks."""
    return CommandPermissions(participant_repository)


def get_relay_engine(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    relay_edge_repository: Annotated[RelayEdgeRepository, Depends(get_relay_edge_repository)],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    runtime_service: Annotated[RuntimeService, Depends(get_runtime_service)],
    thread_mapping_service: Annotated[ThreadMappingService, Depends(get_thread_mapping_service)],
    bridge: Annotated[JsonRpcClient, Depends(get_codex_bridge_client)],
) -> RelayEngine:
    """Provide the relay engine."""
    return RelayEngine(
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        relay_edge_repository=relay_edge_repository,
        message_repository=message_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        agent_repository=agent_repository,
        runtime_service=runtime_service,
        thread_mapping_service=thread_mapping_service,
        bridge=bridge,
    )


def get_command_handler(
    job_service: Annotated[JobService, Depends(get_job_service)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    participant_repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
    agent_repository: Annotated[AgentRepository, Depends(get_agent_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    session_event_repository: Annotated[
        SessionEventRepository, Depends(get_session_event_repository)
    ],
    permissions: Annotated[CommandPermissions, Depends(get_command_permissions)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
) -> CommandHandler:
    """Provide the command handler."""
    return CommandHandler(
        job_service=job_service,
        job_repository=job_repository,
        participant_repository=participant_repository,
        agent_repository=agent_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        permissions=permissions,
        relay_engine=relay_engine,
    )


def get_session_event_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> SessionEventRepository:
    """Provide a session event repository bound to the configured database."""
    return SessionEventRepository(database_url)


def get_relay_edge_repository(
    database_url: Annotated[str, Depends(get_database_url)],
) -> RelayEdgeRepository:
    """Provide a relay edge repository bound to the configured database."""
    return RelayEdgeRepository(database_url)
