"""API models for presence heartbeats."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PresenceHeartbeatRequest(BaseModel):
    """Payload for posting a heartbeat."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str | None = None
    presence: str = "online"
    details: dict[str, object] | None = None
    heartbeat_at: str | None = None


class PresenceHeartbeatResponse(BaseModel):
    """Presence heartbeat response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    runtime_id: str | None
    presence: str
    heartbeat_at: str
    details: dict[str, object] | None = None
    created_at: str


class PresenceEnvelope(BaseModel):
    """Presence response envelope."""

    model_config = ConfigDict(extra="forbid")

    presence: PresenceHeartbeatResponse
