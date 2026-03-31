"""API models for collaboration rules."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuleType = Literal["relay", "review_required", "approval_escalation", "channel_routing_preference"]


class RuleCreateRequest(BaseModel):
    """Payload for creating a rule."""

    model_config = ConfigDict(extra="forbid")

    rule_type: RuleType
    name: str = Field(min_length=1)
    description: str | None = None
    priority: int = 100
    is_active: bool = False
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None


class RuleResponse(BaseModel):
    """Rule response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    rule_type: RuleType
    name: str
    description: str | None
    is_active: bool
    priority: int
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class RuleEnvelope(BaseModel):
    """Single rule response envelope."""

    model_config = ConfigDict(extra="forbid")

    rule: RuleResponse


class RuleListEnvelope(BaseModel):
    """Rule list response envelope."""

    model_config = ConfigDict(extra="forbid")

    rules: list[RuleResponse]
