from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models.api.jobs import ApprovalRequestResponse, JobResponse
from app.models.api.phases import PhaseResponse

OperatorActionKind = Literal[
    "approve",
    "reject",
    "retry",
    "resume",
    "cancel",
    "activate_phase",
]
OperatorActionOutcome = Literal["applied", "duplicate", "failed"]
OperatorActionTargetType = Literal["approval", "job", "phase"]


class OperatorActionRequest(BaseModel):
    """Common payload for operator write actions."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str | None = None
    reason: str | None = None
    note: str | None = None
    context: dict[str, Any] | None = None


class OperatorActionAuditResponse(BaseModel):
    """Persisted audit trail for an operator action."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    actor_type: str | None = None
    actor_id: str | None = None
    actor_role: str | None = None
    actor_label: str | None = None
    identity_source: str | None = None
    auth_mode: str | None = None
    client_host: str | None = None
    session_id: str
    target_type: OperatorActionTargetType
    target_id: str
    result: OperatorActionOutcome
    reason: str | None = None
    note: str | None = None
    failure_mode: str | None = None
    detail: str | None = None
    created_at: str


class OperatorActionResponse(BaseModel):
    """Unified response envelope for operator actions."""

    model_config = ConfigDict(extra="forbid")

    action: OperatorActionKind
    outcome: OperatorActionOutcome
    session_id: str
    target_type: OperatorActionTargetType
    target_id: str
    target_state_before: str | None = None
    target_state_after: str | None = None
    message: str
    audit: OperatorActionAuditResponse
    job: JobResponse | None = None
    approval: ApprovalRequestResponse | None = None
    phase: PhaseResponse | None = None


class OperatorActionEnvelope(BaseModel):
    """Single operator action response."""

    model_config = ConfigDict(extra="forbid")

    action: OperatorActionResponse
