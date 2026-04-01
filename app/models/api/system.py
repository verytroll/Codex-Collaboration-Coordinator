"""API models for system and discovery endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response payload."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


SystemHealth = Literal["ok", "degraded", "unavailable"]


class SystemAppInfoResponse(BaseModel):
    """Application identity for operator-facing system endpoints."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    env: str


class SystemComponentResponse(BaseModel):
    """Health check detail for a coordinator subsystem."""

    model_config = ConfigDict(extra="forbid")

    status: SystemHealth
    detail: str | None = None


class DeploymentReadinessCheckResponse(BaseModel):
    """Readiness check for a single deployment dependency."""

    model_config = ConfigDict(extra="forbid")

    status: SystemHealth
    detail: str | None = None


class DeploymentReadinessChecksResponse(BaseModel):
    """Deployment readiness checks for the app runtime."""

    model_config = ConfigDict(extra="forbid")

    db: DeploymentReadinessCheckResponse
    migrations: DeploymentReadinessCheckResponse


class DeploymentReadinessResponse(BaseModel):
    """Readiness response for deployment and container probes."""

    model_config = ConfigDict(extra="forbid")

    status: SystemHealth
    app: SystemAppInfoResponse
    checks: DeploymentReadinessChecksResponse


class SystemJobSummaryResponse(BaseModel):
    """Aggregate counts for jobs by status."""

    model_config = ConfigDict(extra="forbid")

    queued: int = 0
    running: int = 0
    input_required: int = 0
    auth_required: int = 0
    paused_by_loop_guard: int = 0
    completed: int = 0
    failed: int = 0
    canceled: int = 0


class SystemAggregatesResponse(BaseModel):
    """Top-level coordinator aggregates shown in system status."""

    model_config = ConfigDict(extra="forbid")

    active_sessions: int
    registered_agents: int
    jobs: SystemJobSummaryResponse
    pending_approvals: int
    pending_reviews: int = 0
    runtimes_by_status: dict[str, int] = Field(default_factory=dict)
    active_phase_durations: dict[str, float] = Field(default_factory=dict)
    average_job_latency_seconds: float | None = None
    average_review_wait_seconds: float | None = None


class SystemChecksResponse(BaseModel):
    """Subsystem checks for status and diagnostics."""

    model_config = ConfigDict(extra="forbid")

    db: SystemComponentResponse
    codex_bridge: SystemComponentResponse


class SystemStatusResponse(BaseModel):
    """Coordinator status summary for operators."""

    model_config = ConfigDict(extra="forbid")

    status: SystemHealth
    app: SystemAppInfoResponse
    checks: SystemChecksResponse
    aggregates: SystemAggregatesResponse
    diagnostics: list[str] = Field(default_factory=list)
    telemetry: "TelemetrySurfaceResponse"


class DebugSessionResponse(BaseModel):
    """Condensed session data for debug surfaces."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    status: str
    lead_agent_id: str | None
    updated_at: str
    last_message_at: str | None


class DebugJobResponse(BaseModel):
    """Condensed job data for queued/running/blocked surfaces."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    assigned_agent_id: str
    title: str
    status: str
    priority: str
    codex_thread_id: str | None
    active_turn_id: str | None
    last_known_turn_status: str | None
    updated_at: str


class DebugApprovalResponse(BaseModel):
    """Condensed approval data for pending approval surfaces."""

    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    agent_id: str
    approval_type: str
    status: str
    requested_at: str
    updated_at: str


class DebugSurfaceResponse(BaseModel):
    """Detailed operator-facing diagnostics payload."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    codex_bridge: SystemComponentResponse
    runtime_statuses: dict[str, int] = Field(default_factory=dict)
    active_sessions: list[DebugSessionResponse] = Field(default_factory=list)
    queued_jobs: list[DebugJobResponse] = Field(default_factory=list)
    running_jobs: list[DebugJobResponse] = Field(default_factory=list)
    blocked_jobs: list[DebugJobResponse] = Field(default_factory=list)
    pending_approvals: list[DebugApprovalResponse] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    telemetry: "TelemetrySurfaceResponse"


class TelemetrySampleResponse(BaseModel):
    """Single telemetry sample within the recent timeline."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    generated_at: str
    status: str
    correlation: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)


class TelemetrySurfaceResponse(BaseModel):
    """Live/recent telemetry surface for operator diagnostics."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    window_size: int
    sample_counts: dict[str, int] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    latest: dict[str, TelemetrySampleResponse] = Field(default_factory=dict)
    recent_samples: list[TelemetrySampleResponse] = Field(default_factory=list)


class A2AAgentCardCapabilities(BaseModel):
    """Discovery capabilities advertised for A2A-ready clients."""

    model_config = ConfigDict(extra="forbid")

    streaming: bool = True
    push_notifications: bool = False
    task_delegation: bool = True
    artifacts: bool = True


class A2AAgentCardSkill(BaseModel):
    """Skill descriptor advertised by the placeholder agent card."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str


class A2AAgentCardResponse(BaseModel):
    """Agent card payload for discovery clients."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    version: str
    capabilities: A2AAgentCardCapabilities
    skills: list[A2AAgentCardSkill] = Field(default_factory=list)
