"""Actor identity resolution and role-based authorization."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from fastapi import Request

from app.core.config import AppConfig
from app.core.errors import ForbiddenAccessError, UnauthorizedAccessError
from app.models.api.identity import ActorRole

_OPERATOR_WRITE_ROLES = {"operator", "admin"}
_APPROVAL_WRITE_ROLES = {"operator", "reviewer", "admin"}
_PUBLIC_WRITE_ROLES = {"integration_client", "operator", "admin"}
_VALID_ROLES = {
    "operator",
    "reviewer",
    "integration_client",
    "admin",
}
_VALID_ACTOR_TYPES = {"human", "service"}


@dataclass(frozen=True, slots=True)
class ActorIdentity:
    """Resolved actor identity for a request."""

    actor_id: str
    actor_role: ActorRole
    actor_type: str
    display_label: str | None
    source: str
    auth_mode: str
    client_host: str | None = None

    def as_payload(self) -> dict[str, object]:
        """Return a JSON-serializable payload for audit and logging."""
        return asdict(self)


class AuthzService:
    """Resolve actor identity and enforce basic role checks."""

    def __init__(self, *, config: AppConfig) -> None:
        self.config = config

    async def resolve_operator_identity(self, request: Request) -> ActorIdentity:
        """Resolve an identity for operator write actions."""
        return await self._resolve_identity(
            request,
            bootstrap_role="operator",
            bootstrap_label=self.config.actor_label,
        )

    async def resolve_public_identity(self, request: Request) -> ActorIdentity:
        """Resolve an identity for public write actions."""
        return await self._resolve_identity(
            request,
            bootstrap_role="integration_client",
            bootstrap_label="Public integration client",
        )

    async def resolve_review_identity(self, request: Request) -> ActorIdentity:
        """Resolve an identity for approval/review actions."""
        return await self._resolve_identity(
            request,
            bootstrap_role="reviewer",
            bootstrap_label="Review operator",
        )

    def require_operator_action(self, identity: ActorIdentity, *, action: str) -> None:
        """Allow only operator/admin roles for destructive operator actions."""
        if identity.actor_role not in _OPERATOR_WRITE_ROLES:
            raise ForbiddenAccessError(
                f"Actor role {identity.actor_role} cannot perform {action}",
                details={
                    "action": action,
                    "actor_role": identity.actor_role,
                    "allowed_roles": sorted(_OPERATOR_WRITE_ROLES),
                },
            )

    def require_approval_action(self, identity: ActorIdentity, *, action: str) -> None:
        """Allow operator, reviewer, and admin roles for approval actions."""
        if identity.actor_role not in _APPROVAL_WRITE_ROLES:
            raise ForbiddenAccessError(
                f"Actor role {identity.actor_role} cannot perform {action}",
                details={
                    "action": action,
                    "actor_role": identity.actor_role,
                    "allowed_roles": sorted(_APPROVAL_WRITE_ROLES),
                },
            )

    def require_public_write(self, identity: ActorIdentity, *, action: str) -> None:
        """Allow integration client, operator, and admin roles for public writes."""
        if identity.actor_role not in _PUBLIC_WRITE_ROLES:
            raise ForbiddenAccessError(
                f"Actor role {identity.actor_role} cannot perform {action}",
                details={
                    "action": action,
                    "actor_role": identity.actor_role,
                    "allowed_roles": sorted(_PUBLIC_WRITE_ROLES),
                },
            )

    def actor_payload(self, identity: ActorIdentity) -> dict[str, object]:
        """Return a normalized audit payload for the resolved identity."""
        return identity.as_payload()

    def _client_host(self, request: Request) -> str | None:
        client = request.client
        if client is None:
            return None
        host = client.host.strip()
        return host or None

    def _header_value(self, request: Request, header_name: str) -> str | None:
        value = request.headers.get(header_name)
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    async def _resolve_identity(
        self,
        request: Request,
        *,
        bootstrap_role: ActorRole,
        bootstrap_label: str,
    ) -> ActorIdentity:
        auth_mode = self.config.access_boundary_mode
        client_host = self._client_host(request)
        actor_id = self._header_value(request, self.config.actor_id_header)
        actor_role = self._header_value(request, self.config.actor_role_header)
        actor_type = self._header_value(request, self.config.actor_type_header)
        display_label = self._header_value(request, self.config.actor_label_header)

        if actor_id is None and actor_role is None and actor_type is None and display_label is None:
            if auth_mode in {"local", "trusted"}:
                identity = ActorIdentity(
                    actor_id=f"{bootstrap_role}_bootstrap",
                    actor_role=bootstrap_role,
                    actor_type="service" if bootstrap_role == "integration_client" else "human",
                    display_label=bootstrap_label,
                    source="bootstrap",
                    auth_mode=auth_mode,
                    client_host=client_host,
                )
                request.state.actor_identity = identity
                request.state.actor_role = identity.actor_role
                request.state.actor_id = identity.actor_id
                request.state.actor_type = identity.actor_type
                request.state.actor_source = identity.source
                return identity
            raise UnauthorizedAccessError(
                "Actor identity is required for protected writes",
                details={
                    "reason": "missing_identity",
                    "mode": auth_mode,
                    "required_headers": [
                        self.config.actor_id_header,
                        self.config.actor_role_header,
                    ],
                },
            )

        if actor_id is None or actor_role is None:
            raise UnauthorizedAccessError(
                "Actor identity headers are incomplete",
                details={
                    "reason": "missing_identity",
                    "mode": auth_mode,
                    "required_headers": [
                        self.config.actor_id_header,
                        self.config.actor_role_header,
                    ],
                },
            )

        normalized_role = actor_role.strip().lower()
        if normalized_role not in _VALID_ROLES:
            raise ForbiddenAccessError(
                f"Actor role {normalized_role} is not supported",
                details={
                    "reason": "invalid_role",
                    "actor_role": normalized_role,
                    "allowed_roles": sorted(_VALID_ROLES),
                },
            )

        normalized_type = (actor_type or "").strip().lower()
        if normalized_type not in _VALID_ACTOR_TYPES:
            normalized_type = "service" if normalized_role == "integration_client" else "human"

        identity = ActorIdentity(
            actor_id=actor_id,
            actor_role=normalized_role,
            actor_type=normalized_type,
            display_label=display_label,
            source="headers",
            auth_mode=auth_mode,
            client_host=client_host,
        )
        request.state.actor_identity = identity
        request.state.actor_role = identity.actor_role
        request.state.actor_id = identity.actor_id
        request.state.actor_type = identity.actor_type
        request.state.actor_source = identity.source
        return identity
