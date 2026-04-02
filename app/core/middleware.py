"""Middleware for request-scoped metadata."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logging import (
    bind_log_context,
    clear_access_context,
    get_logger,
    reset_log_context,
    reset_request_id,
    set_request_id,
)

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id to each request and response."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(self.header_name, uuid4().hex)
        token = set_request_id(request_id)
        context_tokens = bind_log_context(
            request_method=request.method,
            request_path=request.url.path,
        )
        request.state.request_id = request_id
        request.state.request_method = request.method
        request.state.request_path = request.url.path
        request.state.actor_identity = None
        request.state.actor_role = None
        request.state.actor_id = None
        request.state.actor_type = None
        request.state.actor_source = None
        started_at = perf_counter()
        logger.info("request.start")
        try:
            response = await call_next(request)
            duration_ms = (perf_counter() - started_at) * 1000.0
            logger.info("request.end status=%s duration_ms=%.2f", response.status_code, duration_ms)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000.0
            logger.exception("request.failed duration_ms=%.2f", duration_ms)
            raise
        finally:
            reset_log_context(context_tokens)
            clear_access_context()
            reset_request_id(token)

        response.headers[self.header_name] = request_id
        return response
