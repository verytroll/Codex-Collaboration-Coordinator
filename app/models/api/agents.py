"""API models for agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

PresenceStatus = Literal["online", "offline", "busy", "unknown"]


class AgentCreateRequest(BaseModel):
    """Payload for creating an agent."""

    model_config = ConfigDict(extra="forbid")

    display_name: str
    role: str
    is_lead: bool = False
    runtime_kind: str = "codex"
    runtime_config: dict[str, Any] | None = None


class AgentUpdateRequest(BaseModel):
    """Payload for updating an agent."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    role: str | None = None
    is_lead: bool | None = None


class AgentResponse(BaseModel):
    """Agent response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    role: str
    is_lead: bool
    runtime_kind: str
    runtime_id: str | None
    presence: PresenceStatus
    capabilities: dict[str, bool]
    created_at: str
    updated_at: str


class AgentEnvelope(BaseModel):
    """Single-agent response envelope."""

    model_config = ConfigDict(extra="forbid")

    agent: AgentResponse


class AgentListEnvelope(BaseModel):
    """Agent list response envelope."""

    model_config = ConfigDict(extra="forbid")

    agents: list[AgentResponse]
