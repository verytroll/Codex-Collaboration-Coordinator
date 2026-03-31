"""Common API error models and handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_request_id


class ApiError(BaseModel):
    """Standard API error payload."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    details: list[Any] | None = None


class ErrorResponse(BaseModel):
    """Response envelope for API errors."""

    error: ApiError


def _build_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> JSONResponse:
    request_id = get_request_id()
    payload = ErrorResponse(
        error=ApiError(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Convert HTTP exceptions into the standard error envelope."""
    message = str(exc.detail) if exc.detail is not None else "HTTP error"
    return _build_response(
        status_code=exc.status_code,
        code="http_error",
        message=message,
    )


async def handle_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert validation errors into the standard error envelope."""
    return _build_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    """Convert unexpected errors into the standard error envelope."""
    return _build_response(
        status_code=500,
        code="internal_server_error",
        message="Internal server error",
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register the common API error handlers on the app."""
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
