"""API models for advanced policy automation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PolicyType = Literal[
    "conditional_auto_approve",
    "escalation",
    "template_scoped",
    "phase_scoped",
]
PolicyDecisionType = Literal[
    "allow",
    "auto_approve",
    "escalate_review",
    "paused",
    "resumed",
    "deferred",
]
PolicySubjectType = Literal["approval_gate", "review_gate", "policy_control"]
PolicyGateType = Literal["approval_required", "review_required", "automation_control"]


class PolicyCreateRequest(BaseModel):
    """Payload for creating a policy."""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    template_key: str | None = None
    phase_key: str | None = None
    policy_type: PolicyType
    name: str = Field(min_length=1)
    description: str | None = None
    is_active: bool = True
    automation_paused: bool = False
    pause_reason: str | None = None
    priority: int = 100
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None


class PolicyControlRequest(BaseModel):
    """Payload for pausing or resuming automation."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class PolicyResponse(BaseModel):
    """Policy response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str | None = None
    template_key: str | None = None
    phase_key: str | None = None
    policy_type: PolicyType
    name: str
    description: str | None = None
    is_active: bool
    automation_paused: bool
    pause_reason: str | None = None
    priority: int
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class PolicyEnvelope(BaseModel):
    """Single policy response envelope."""

    model_config = ConfigDict(extra="forbid")

    policy: PolicyResponse


class PolicyListEnvelope(BaseModel):
    """Policy list response envelope."""

    model_config = ConfigDict(extra="forbid")

    policies: list[PolicyResponse] = Field(default_factory=list)


class PolicyDecisionResponse(BaseModel):
    """Policy decision audit payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    policy_id: str | None = None
    session_id: str | None = None
    subject_type: PolicySubjectType
    subject_id: str
    gate_type: PolicyGateType
    decision: PolicyDecisionType
    matched: bool
    reason: str
    context: dict[str, Any]
    created_at: str


class PolicyDecisionListEnvelope(BaseModel):
    """Policy decision list response envelope."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[PolicyDecisionResponse] = Field(default_factory=list)


class PolicyDecisionEnvelope(BaseModel):
    """Single policy decision response envelope."""

    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecisionResponse
