"""FastAPI dependencies for repository access."""

from __future__ import annotations

from fastapi import Depends

from app.core.config import get_config
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.presence import PresenceRepository
from app.repositories.sessions import SessionRepository


def get_database_url() -> str:
    """Return the active database URL from application config."""
    return get_config().database_url


def get_session_repository(
    database_url: str = Depends(get_database_url),
) -> SessionRepository:
    """Provide a session repository bound to the configured database."""
    return SessionRepository(database_url)


def get_agent_repository(
    database_url: str = Depends(get_database_url),
) -> AgentRepository:
    """Provide an agent repository bound to the configured database."""
    return AgentRepository(database_url)


def get_agent_runtime_repository(
    database_url: str = Depends(get_database_url),
) -> AgentRuntimeRepository:
    """Provide an agent runtime repository bound to the configured database."""
    return AgentRuntimeRepository(database_url)


def get_presence_repository(
    database_url: str = Depends(get_database_url),
) -> PresenceRepository:
    """Provide a presence repository bound to the configured database."""
    return PresenceRepository(database_url)
