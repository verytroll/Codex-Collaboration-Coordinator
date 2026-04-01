"""API models for runtime pools and isolated work contexts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuntimePoolStatus = Literal["ready", "degraded", "offline"]
RuntimePoolIsolationMode = Literal["shared", "isolated", "ephemeral"]
WorkContextStatus = Literal[
    "active",
    "waiting_for_runtime",
    "fallback",
    "recovered",
    "released",
    "failed",
]
WorkContextOwnership = Literal["owned", "borrowed", "released"]


class RuntimePoolCreateRequest(BaseModel):
    """Payload for creating a runtime pool."""

    model_config = ConfigDict(extra="forbid")

    pool_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    runtime_kind: str = "codex"
    preferred_transport_kind: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    fallback_pool_key: str | None = None
    max_active_contexts: int = 1
    default_isolation_mode: RuntimePoolIsolationMode = "isolated"
    pool_status: RuntimePoolStatus = "ready"
    metadata: dict[str, Any] | None = None
    is_default: bool = False
    sort_order: int = 100


class RuntimePoolAssignRequest(BaseModel):
    """Payload for assigning a job into a runtime pool."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    preferred_pool_key: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)


class WorkContextRecoverRequest(BaseModel):
    """Payload for recovering a work context."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class RuntimePoolResponse(BaseModel):
    """Runtime pool response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    pool_key: str
    title: str
    description: str | None = None
    runtime_kind: str
    preferred_transport_kind: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    fallback_pool_key: str | None = None
    max_active_contexts: int
    default_isolation_mode: RuntimePoolIsolationMode
    pool_status: RuntimePoolStatus
    metadata: dict[str, Any] | None = None
    is_default: bool
    sort_order: int
    active_context_count: int = 0
    waiting_context_count: int = 0
    borrowed_context_count: int = 0
    available_runtime_count: int = 0
    utilization_ratio: float = 0.0
    created_at: str
    updated_at: str


class WorkContextResponse(BaseModel):
    """Work context response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    job_id: str
    agent_id: str
    runtime_pool_key: str
    runtime_id: str | None = None
    context_key: str
    workspace_path: str | None = None
    isolation_mode: RuntimePoolIsolationMode
    context_status: WorkContextStatus
    ownership_state: WorkContextOwnership
    selection_reason: str | None = None
    failure_reason: str | None = None
    created_at: str
    updated_at: str


class RuntimePoolEnvelope(BaseModel):
    """Single runtime pool response envelope."""

    model_config = ConfigDict(extra="forbid")

    pool: RuntimePoolResponse


class RuntimePoolListEnvelope(BaseModel):
    """Runtime pool list response envelope."""

    model_config = ConfigDict(extra="forbid")

    pools: list[RuntimePoolResponse] = Field(default_factory=list)


class RuntimePoolDiagnosticsResponse(BaseModel):
    """Runtime pool diagnostics payload."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    total_pools: int
    total_contexts: int
    owned_contexts: int
    borrowed_contexts: int
    released_contexts: int
    pools: list[RuntimePoolResponse] = Field(default_factory=list)


class RuntimePoolDiagnosticsEnvelope(BaseModel):
    """Runtime pool diagnostics response envelope."""

    model_config = ConfigDict(extra="forbid")

    diagnostics: RuntimePoolDiagnosticsResponse


class WorkContextEnvelope(BaseModel):
    """Single work context response envelope."""

    model_config = ConfigDict(extra="forbid")

    context: WorkContextResponse


class WorkContextListEnvelope(BaseModel):
    """Work context list response envelope."""

    model_config = ConfigDict(extra="forbid")

    contexts: list[WorkContextResponse] = Field(default_factory=list)


class RuntimePoolAssignEnvelope(BaseModel):
    """Runtime pool assignment response envelope."""

    model_config = ConfigDict(extra="forbid")

    pool: RuntimePoolResponse
    context: WorkContextResponse
    fallback_used: bool = False
    runtime_found: bool = False

