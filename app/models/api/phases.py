"""API models for phase presets and session phases."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PhasePresetResponse(BaseModel):
    """Phase preset response payload."""

    model_config = ConfigDict(extra="forbid")

    phase_key: str
    title: str
    description: str | None = None
    relay_template_key: str
    default_channel_key: str
    sort_order: int
    is_default: bool


class PhaseResponse(BaseModel):
    """Session phase response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    phase_key: str
    title: str
    description: str | None = None
    relay_template_key: str
    default_channel_key: str
    sort_order: int
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str


class PhasePresetListEnvelope(BaseModel):
    """Phase preset list response envelope."""

    model_config = ConfigDict(extra="forbid")

    presets: list[PhasePresetResponse] = Field(default_factory=list)


class PhaseListEnvelope(BaseModel):
    """Session phase list response envelope."""

    model_config = ConfigDict(extra="forbid")

    phases: list[PhaseResponse] = Field(default_factory=list)


class PhaseEnvelope(BaseModel):
    """Single phase response envelope."""

    model_config = ConfigDict(extra="forbid")

    phase: PhaseResponse
