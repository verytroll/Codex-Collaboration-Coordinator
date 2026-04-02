"""API models for actor identity and authz context."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

ActorRole = Literal["operator", "reviewer", "integration_client", "admin"]
ActorType = Literal["human", "service"]
IdentitySource = Literal["headers", "bootstrap"]


class ActorIdentityResponse(BaseModel):
    """Resolved actor identity for request-scoped authorization."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    actor_role: ActorRole
    actor_type: ActorType
    display_label: str | None = None
    source: IdentitySource
    auth_mode: str
    client_host: str | None = None


ActorIdentity = ActorIdentityResponse
