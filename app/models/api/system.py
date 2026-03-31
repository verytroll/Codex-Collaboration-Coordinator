"""API models for system and discovery endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response payload."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


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
