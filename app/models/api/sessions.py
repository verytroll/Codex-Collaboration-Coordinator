"""API models for sessions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

SessionStatus = Literal["draft", "active", "paused", "completed", "archived"]


class SessionCreateRequest(BaseModel):
    """Payload for creating a session."""

    model_config = ConfigDict(extra="forbid")

    title: str
    goal: str | None = None
    lead_agent_id: str | None = None


class SessionUpdateRequest(BaseModel):
    """Payload for updating a session."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    goal: str | None = None
    status: SessionStatus | None = None
    lead_agent_id: str | None = None
    active_phase_id: str | None = None


class SessionResponse(BaseModel):
    """Session response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    goal: str | None
    status: SessionStatus
    lead_agent_id: str | None
    active_phase_id: str | None
    created_at: str
    updated_at: str


class SessionEnvelope(BaseModel):
    """Single-session response envelope."""

    model_config = ConfigDict(extra="forbid")

    session: SessionResponse


class SessionListEnvelope(BaseModel):
    """Session list response envelope."""

    model_config = ConfigDict(extra="forbid")

    sessions: list[SessionResponse]
