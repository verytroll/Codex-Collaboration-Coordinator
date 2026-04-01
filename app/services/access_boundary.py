"""Access boundary enforcement for operator and public surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.errors import ForbiddenAccessError, UnauthorizedAccessError
from app.core.logging import bind_log_context, get_logger

logger = get_logger(__name__)

DEFAULT_TRUSTED_CLIENT_HOSTS = {
    "127.0.0.1",
    "::1",
    "localhost",
    "testclient",
    "testserver",
}
VALID_ACCESS_BOUNDARY_MODES = {"local", "trusted", "protected"}


@dataclass(frozen=True, slots=True)
class AccessDecision:
    """Resolved access decision for a request."""

    allowed: bool
    result: str
    reason: str
    client_host: str


class AccessBoundaryService:
    """Authorize requests for operator and public surfaces."""

    def __init__(
        self,
        *,
        access_boundary_mode: str,
        access_token: str,
        access_token_header: str,
        trusted_client_hosts: set[str] | None = None,
    ) -> None:
        self.access_boundary_mode = self._normalize_mode(access_boundary_mode)
        self.access_token = access_token.strip()
        self.access_token_header = access_token_header.strip() or "X-Access-Token"
        self.trusted_client_hosts = trusted_client_hosts or DEFAULT_TRUSTED_CLIENT_HOSTS

    async def require_operator_access(self, request: Request) -> None:
        """Authorize a request to the operator surface."""
        await self._authorize(request, surface="operator")

    async def require_public_access(self, request: Request) -> None:
        """Authorize a request to the public/A2A surface."""
        await self._authorize(request, surface="public")

    def _normalize_mode(self, access_boundary_mode: str) -> str:
        normalized = access_boundary_mode.strip().lower()
        if normalized in VALID_ACCESS_BOUNDARY_MODES:
            return normalized
        return "trusted"

    def _client_host(self, request: Request) -> str:
        client = request.client
        if client is None:
            return "-"
        host = client.host.strip()
        return host or "-"

    def _is_trusted_client(self, client_host: str) -> bool:
        return client_host in self.trusted_client_hosts

    def _extract_token(self, request: Request) -> str | None:
        token = request.headers.get(self.access_token_header)
        if token is not None:
            stripped = token.strip()
            if stripped:
                return stripped

        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        prefix = "bearer "
        if authorization.lower().startswith(prefix):
            bearer_token = authorization[len(prefix) :].strip()
            return bearer_token or None
        return authorization.strip() or None

    def _token_matches(self, token: str | None) -> bool:
        return token is not None and self.access_token != "" and token == self.access_token

    def _bind_access_context(
        self,
        *,
        surface: str,
        decision: AccessDecision,
    ) -> None:
        bind_log_context(
            access_mode=self.access_boundary_mode,
            access_surface=surface,
            access_result=decision.result,
            access_reason=decision.reason,
            client_host=decision.client_host,
        )

    def _log_allowed(self, *, surface: str, decision: AccessDecision) -> None:
        self._bind_access_context(surface=surface, decision=decision)
        logger.info(
            "access.allowed surface=%s mode=%s reason=%s client_host=%s",
            surface,
            self.access_boundary_mode,
            decision.reason,
            decision.client_host,
        )

    def _log_denied(self, *, surface: str, decision: AccessDecision) -> None:
        self._bind_access_context(surface=surface, decision=decision)
        logger.warning(
            "access.denied surface=%s mode=%s reason=%s client_host=%s",
            surface,
            self.access_boundary_mode,
            decision.reason,
            decision.client_host,
        )

    async def _authorize(self, request: Request, *, surface: str) -> None:
        client_host = self._client_host(request)
        token = self._extract_token(request)
        trusted_client = self._is_trusted_client(client_host)

        if self.access_boundary_mode == "local":
            self._log_allowed(
                surface=surface,
                decision=AccessDecision(
                    allowed=True,
                    result="allowed",
                    reason="local_mode",
                    client_host=client_host,
                ),
            )
            return

        if self.access_boundary_mode == "trusted" and trusted_client and token is None:
            self._log_allowed(
                surface=surface,
                decision=AccessDecision(
                    allowed=True,
                    result="allowed",
                    reason="trusted_client",
                    client_host=client_host,
                ),
            )
            return

        if token is None:
            decision = AccessDecision(
                allowed=False,
                result="unauthorized",
                reason="missing_token",
                client_host=client_host,
            )
            self._log_denied(surface=surface, decision=decision)
            raise UnauthorizedAccessError(
                f"{surface.capitalize()} access requires a valid access token",
                details={
                    "surface": surface,
                    "mode": self.access_boundary_mode,
                    "client_host": client_host,
                    "reason": "missing_token",
                },
            )

        if self._token_matches(token):
            self._log_allowed(
                surface=surface,
                decision=AccessDecision(
                    allowed=True,
                    result="allowed",
                    reason="service_token",
                    client_host=client_host,
                ),
            )
            return

        decision = AccessDecision(
            allowed=False,
            result="forbidden",
            reason="invalid_token",
            client_host=client_host,
        )
        self._log_denied(surface=surface, decision=decision)
        raise ForbiddenAccessError(
            f"{surface.capitalize()} access token is not valid",
            details={
                "surface": surface,
                "mode": self.access_boundary_mode,
                "client_host": client_host,
                "reason": "invalid_token",
            },
        )
