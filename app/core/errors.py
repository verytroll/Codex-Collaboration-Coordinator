"""Common API error models and handlers."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_request_id


class AppError(Exception):
    """Base class for domain errors that should map to a standard API envelope."""

    status_code: int = 500
    error_code: str = "app_error"

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError, LookupError):
    """Raised when a requested resource is missing."""

    status_code = 404
    error_code = "not_found"


class ConflictError(AppError, ValueError):
    """Raised when a state transition cannot be applied safely."""

    status_code = 409
    error_code = "conflict"


class BadRequestError(AppError, ValueError):
    """Raised when a request is structurally valid but cannot be applied."""

    status_code = 400
    error_code = "bad_request"


class ServiceUnavailableError(AppError, RuntimeError):
    """Raised when an external dependency cannot be reached safely."""

    status_code = 503
    error_code = "service_unavailable"


class UnauthorizedAccessError(AppError, PermissionError):
    """Raised when a protected surface is missing valid credentials."""

    status_code = 401
    error_code = "access_unauthorized"


class ForbiddenAccessError(AppError, PermissionError):
    """Raised when supplied credentials are not allowed."""

    status_code = 403
    error_code = "access_forbidden"


class ApiError(BaseModel):
    """Standard API error payload."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Response envelope for API errors."""

    error: ApiError


def _build_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
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


def _build_http_error_response(exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        return _build_response(
            status_code=exc.status_code,
            code="http_error",
            message=detail,
        )
    return _build_response(
        status_code=exc.status_code,
        code="http_error",
        message=HTTPStatus(exc.status_code).phrase,
        details=detail,
    )


def _build_app_error_response(exc: AppError) -> JSONResponse:
    return _build_response(
        status_code=exc.status_code,
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Convert HTTP exceptions into the standard error envelope."""
    return _build_http_error_response(exc)


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


async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    """Convert domain errors into the standard error envelope."""
    return _build_app_error_response(exc)


def install_error_handlers(app: FastAPI) -> None:
    """Register the common API error handlers on the app."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
