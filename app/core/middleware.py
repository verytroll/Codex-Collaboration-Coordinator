"""Middleware for request-scoped metadata."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi import Request

from app.core.logging import reset_request_id, set_request_id

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


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
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)

        response.headers[self.header_name] = request_id
        return response
