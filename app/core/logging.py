"""Logging helpers."""

from __future__ import annotations

import contextvars
import logging
from typing import Final

REQUEST_ID_DEFAULT: Final[str] = "-"
REQUEST_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default=REQUEST_ID_DEFAULT,
)


def set_request_id(request_id: str) -> contextvars.Token[str]:
    """Set the active request id for the current context."""
    return REQUEST_ID_CONTEXT.set(request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    """Reset the active request id after a request completes."""
    REQUEST_ID_CONTEXT.reset(token)


def get_request_id() -> str:
    """Read the active request id from context."""
    return REQUEST_ID_CONTEXT.get()


class RequestIdFilter(logging.Filter):
    """Inject the request id into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: str) -> None:
    """Configure the root logger with a request-id aware formatter."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        )
    )
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured to work with the global logging setup."""
    return logging.getLogger(name)
