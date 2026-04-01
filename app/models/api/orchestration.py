"""API models for orchestration runs and gated transitions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrchestrationGateType = Literal[
    "review_required",
    "approval_required",
    "revise_on_reject",
]
OrchestrationRunStatus = Literal["active", "blocked", "completed"]
OrchestrationGateStatus = Literal["idle", "pending", "approved", "rejected"]


class OrchestrationRunResponse(BaseModel):
    """Orchestration run response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    status: OrchestrationRunStatus
    current_phase_id: str | None
    current_phase_key: str
    pending_phase_key: str | None
    failure_phase_key: str
    gate_type: OrchestrationGateType | None = None
    gate_status: OrchestrationGateStatus
    source_job_id: str | None
    handoff_job_id: str | None
    review_id: str | None
    approval_id: str | None
    transition_artifact_id: str | None
    decision_artifact_id: str | None
    revision_job_id: str | None
    requested_by_agent_id: str | None
    transition_reason: str | None
    started_at: str
    decided_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str


class OrchestrationRunEnvelope(BaseModel):
    """Single orchestration run response envelope."""

    model_config = ConfigDict(extra="forbid")

    run: OrchestrationRunResponse


class OrchestrationRunListEnvelope(BaseModel):
    """Orchestration run list response envelope."""

    model_config = ConfigDict(extra="forbid")

    runs: list[OrchestrationRunResponse] = Field(default_factory=list)


class OrchestrationGateRequest(BaseModel):
    """Payload for opening a gated transition."""

    model_config = ConfigDict(extra="forbid")

    source_job_id: str
    gate_type: OrchestrationGateType
    success_phase_key: str = "finalize"
    failure_phase_key: str = "revise"
    reviewer_agent_id: str | None = None
    approver_agent_id: str | None = None
    requested_by_agent_id: str | None = None
    notes: str | None = None


class OrchestrationGateEnvelope(BaseModel):
    """Gated transition response envelope."""

    model_config = ConfigDict(extra="forbid")

    run: OrchestrationRunResponse
    source_job_id: str
    handoff_job_id: str | None = None
    review_id: str | None = None
    approval_id: str | None = None
    transition_artifact_id: str
