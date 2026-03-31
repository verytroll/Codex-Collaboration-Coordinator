"""API models for session participants."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

ParticipantRole = Literal["planner", "builder", "reviewer", "researcher", "tester"]


class ParticipantPolicyRequest(BaseModel):
    """Optional participant policy overrides."""

    model_config = ConfigDict(extra="forbid")

    can_relay: bool | None = None
    can_create_job: bool | None = None
    can_interrupt: bool | None = None
    can_compact: bool | None = None
    review_only_actions: bool | None = None
    can_target_other_agents: bool | None = None


class ParticipantPolicyResponse(BaseModel):
    """Effective participant policy payload."""

    model_config = ConfigDict(extra="forbid")

    can_relay: bool
    can_create_job: bool
    can_interrupt: bool
    can_compact: bool
    review_only_actions: bool
    can_target_other_agents: bool


class ParticipantCreateRequest(BaseModel):
    """Payload for adding a participant to a session."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    role: ParticipantRole | None = None
    policy: ParticipantPolicyRequest | None = None


class ParticipantUpdateRequest(BaseModel):
    """Payload for updating a participant's session role or policy."""

    model_config = ConfigDict(extra="forbid")

    role: ParticipantRole | None = None
    policy: ParticipantPolicyRequest | None = None


class ParticipantResponse(BaseModel):
    """Participant response payload."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    agent_id: str
    agent_role: str
    role: ParticipantRole
    is_lead: bool
    participant_status: str
    joined_at: str
    read_scope: str
    write_scope: str
    policy: ParticipantPolicyResponse


class ParticipantEnvelope(BaseModel):
    """Single participant response envelope."""

    model_config = ConfigDict(extra="forbid")

    participant: ParticipantResponse


class ParticipantListEnvelope(BaseModel):
    """Participant list response envelope."""

    model_config = ConfigDict(extra="forbid")

    participants: list[ParticipantResponse]
