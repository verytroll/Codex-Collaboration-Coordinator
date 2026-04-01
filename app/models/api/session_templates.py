"""API models for session templates and orchestration presets."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.rules import RuleType
from app.models.api.sessions import SessionResponse


class SessionTemplateChannelSpec(BaseModel):
    """Channel preset for a session template."""

    model_config = ConfigDict(extra="forbid")

    channel_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str | None = None
    sort_order: int = 0
    is_default: bool = False


class SessionTemplatePhaseSpec(BaseModel):
    """Phase ordering preset for a session template."""

    model_config = ConfigDict(extra="forbid")

    phase_key: str = Field(min_length=1)
    sort_order: int = 0


class SessionTemplateRulePresetSpec(BaseModel):
    """Rule preset for a session template."""

    model_config = ConfigDict(extra="forbid")

    rule_type: RuleType
    name: str = Field(min_length=1)
    description: str | None = None
    priority: int = 100
    is_active: bool = False
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None


class SessionTemplateOrchestrationSpec(BaseModel):
    """Orchestration preset metadata for a session template."""

    model_config = ConfigDict(extra="forbid")

    default_active_phase_key: str | None = None


class SessionTemplateCreateRequest(BaseModel):
    """Payload for creating a session template."""

    model_config = ConfigDict(extra="forbid")

    template_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    default_goal: str | None = None
    participant_roles: list[str] = Field(default_factory=list)
    channels: list[SessionTemplateChannelSpec] = Field(default_factory=list)
    phase_order: list[SessionTemplatePhaseSpec] = Field(default_factory=list)
    rule_presets: list[SessionTemplateRulePresetSpec] = Field(default_factory=list)
    orchestration: SessionTemplateOrchestrationSpec | None = None
    is_default: bool = False
    sort_order: int = 100


class SessionTemplateInstantiateRequest(BaseModel):
    """Payload for instantiating a session from a template."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    goal: str | None = None
    lead_agent_id: str | None = None


class SessionTemplateResponse(BaseModel):
    """Session template response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    template_key: str
    title: str
    description: str | None = None
    default_goal: str | None = None
    participant_roles: list[str] = Field(default_factory=list)
    channels: list[SessionTemplateChannelSpec] = Field(default_factory=list)
    phase_order: list[SessionTemplatePhaseSpec] = Field(default_factory=list)
    rule_presets: list[SessionTemplateRulePresetSpec] = Field(default_factory=list)
    orchestration: SessionTemplateOrchestrationSpec | None = None
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str


class SessionTemplateEnvelope(BaseModel):
    """Single session template response envelope."""

    model_config = ConfigDict(extra="forbid")

    template: SessionTemplateResponse


class SessionTemplateListEnvelope(BaseModel):
    """Session template list response envelope."""

    model_config = ConfigDict(extra="forbid")

    templates: list[SessionTemplateResponse] = Field(default_factory=list)


class SessionTemplateInstantiateEnvelope(BaseModel):
    """Session template instantiation response envelope."""

    model_config = ConfigDict(extra="forbid")

    session: SessionResponse
