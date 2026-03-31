"""API models for session participants."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ParticipantCreateRequest(BaseModel):
    """Payload for adding a participant to a session."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str


class ParticipantResponse(BaseModel):
    """Participant response payload."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    agent_id: str
    joined_at: str
    read_scope: str
    write_scope: str


class ParticipantEnvelope(BaseModel):
    """Single participant response envelope."""

    model_config = ConfigDict(extra="forbid")

    participant: ParticipantResponse


class ParticipantListEnvelope(BaseModel):
    """Participant list response envelope."""

    model_config = ConfigDict(extra="forbid")

    participants: list[ParticipantResponse]
