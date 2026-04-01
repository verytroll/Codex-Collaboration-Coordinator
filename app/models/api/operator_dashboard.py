"""API models for the operator dashboard and debug surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.runtime_pools import RuntimePoolStatus
from app.models.api.system import DebugSurfaceResponse, TelemetrySurfaceResponse

OperatorBottleneckKind = Literal["phase", "runtime_pool", "review"]


class OperatorDashboardFiltersResponse(BaseModel):
    """Filters applied to dashboard aggregates."""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    template_key: str | None = None
    phase_key: str | None = None
    runtime_pool_key: str | None = None


class OperatorBottleneckResponse(BaseModel):
    """Short summary of a bottleneck surface."""

    model_config = ConfigDict(extra="forbid")

    kind: OperatorBottleneckKind
    key: str
    count: int
    detail: str | None = None


class OperatorQueueHeatResponse(BaseModel):
    """Queue heat grouped by session, phase, and runtime pool."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    session_title: str
    phase_key: str | None = None
    runtime_pool_key: str | None = None
    queued_jobs: int
    running_jobs: int
    blocked_jobs: int
    total_jobs: int


class OperatorPhaseDistributionResponse(BaseModel):
    """Phase distribution across sessions, jobs, reviews, tasks, and gates."""

    model_config = ConfigDict(extra="forbid")

    phase_key: str
    session_count: int
    queued_jobs: int
    running_jobs: int
    blocked_jobs: int
    pending_reviews: int
    pending_gates: int
    task_count: int


class OperatorReviewBottleneckResponse(BaseModel):
    """Pending review bottleneck summary."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    session_title: str
    template_key: str
    review_channel_key: str
    review_scope: str
    pending_reviews: int
    oldest_requested_at: str | None = None
    newest_requested_at: str | None = None


class OperatorRuntimePoolHealthResponse(BaseModel):
    """Runtime pool health and queue pressure summary."""

    model_config = ConfigDict(extra="forbid")

    id: str
    pool_key: str
    title: str
    pool_status: RuntimePoolStatus
    max_active_contexts: int
    active_context_count: int
    waiting_context_count: int
    borrowed_context_count: int
    available_runtime_count: int
    utilization_ratio: float
    queued_jobs: int
    blocked_jobs: int
    pending_reviews: int
    pending_tasks: int
    created_at: str
    updated_at: str


class OperatorPublicTaskThroughputResponse(BaseModel):
    """Public task throughput summary."""

    model_config = ConfigDict(extra="forbid")

    total_tasks: int
    queued: int
    running: int
    input_required: int
    auth_required: int
    completed: int
    failed: int
    canceled: int


class OperatorDashboardResponse(BaseModel):
    """Operator-facing dashboard aggregates."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    filters: OperatorDashboardFiltersResponse
    bottlenecks: list[OperatorBottleneckResponse] = Field(default_factory=list)
    queue_heat: list[OperatorQueueHeatResponse] = Field(default_factory=list)
    phase_distribution: list[OperatorPhaseDistributionResponse] = Field(default_factory=list)
    review_bottlenecks: list[OperatorReviewBottleneckResponse] = Field(default_factory=list)
    runtime_pools: list[OperatorRuntimePoolHealthResponse] = Field(default_factory=list)
    public_task_throughput: OperatorPublicTaskThroughputResponse
    diagnostics: list[str] = Field(default_factory=list)
    telemetry: TelemetrySurfaceResponse


class OperatorDebugResponse(BaseModel):
    """Expanded operator debug surface."""

    model_config = ConfigDict(extra="forbid")

    dashboard: OperatorDashboardResponse
    debug: DebugSurfaceResponse
