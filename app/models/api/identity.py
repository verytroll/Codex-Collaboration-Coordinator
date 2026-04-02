"""API models for actor identity and authz context."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ActorRole = Literal["operator", "reviewer", "integration_client", "admin"]
ActorType = Literal["human", "service"]
IdentitySource = Literal["headers", "bootstrap", "credentials"]


class ActorIdentityResponse(BaseModel):
    """Resolved actor identity for request-scoped authorization."""

    model_config = ConfigDict(extra="forbid")

    principal_id: str | None = None
    credential_id: str | None = None
    actor_id: str
    actor_role: ActorRole
    actor_type: ActorType
    display_label: str | None = None
    source: IdentitySource
    auth_mode: str
    credential_scopes: list[str] = Field(default_factory=list)
    credential_status: str | None = None
    client_host: str | None = None


ActorIdentity = ActorIdentityResponse
