"""Logging helpers."""

from __future__ import annotations

import contextvars
import logging
from typing import Final

REQUEST_ID_DEFAULT: Final[str] = "-"
LOG_CONTEXT_DEFAULT: Final[str] = "-"
REQUEST_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default=REQUEST_ID_DEFAULT,
)
SESSION_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "session_id",
    default=LOG_CONTEXT_DEFAULT,
)
AGENT_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "agent_id",
    default=LOG_CONTEXT_DEFAULT,
)
JOB_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "job_id",
    default=LOG_CONTEXT_DEFAULT,
)
CODEX_THREAD_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "codex_thread_id",
    default=LOG_CONTEXT_DEFAULT,
)
EVENT_TYPE_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "event_type",
    default=LOG_CONTEXT_DEFAULT,
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


def bind_log_context(
    *,
    session_id: str | None = None,
    agent_id: str | None = None,
    job_id: str | None = None,
    codex_thread_id: str | None = None,
    event_type: str | None = None,
) -> dict[str, contextvars.Token[str]]:
    """Bind operator-relevant logging fields into the current context."""
    tokens: dict[str, contextvars.Token[str]] = {}
    if session_id is not None:
        tokens["session_id"] = SESSION_ID_CONTEXT.set(session_id)
    if agent_id is not None:
        tokens["agent_id"] = AGENT_ID_CONTEXT.set(agent_id)
    if job_id is not None:
        tokens["job_id"] = JOB_ID_CONTEXT.set(job_id)
    if codex_thread_id is not None:
        tokens["codex_thread_id"] = CODEX_THREAD_ID_CONTEXT.set(codex_thread_id)
    if event_type is not None:
        tokens["event_type"] = EVENT_TYPE_CONTEXT.set(event_type)
    return tokens


def reset_log_context(tokens: dict[str, contextvars.Token[str]]) -> None:
    """Reset previously bound logging fields."""
    for key, token in tokens.items():
        if key == "session_id":
            SESSION_ID_CONTEXT.reset(token)
        elif key == "agent_id":
            AGENT_ID_CONTEXT.reset(token)
        elif key == "job_id":
            JOB_ID_CONTEXT.reset(token)
        elif key == "codex_thread_id":
            CODEX_THREAD_ID_CONTEXT.reset(token)
        elif key == "event_type":
            EVENT_TYPE_CONTEXT.reset(token)


class RequestIdFilter(logging.Filter):
    """Inject the request id into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.session_id = SESSION_ID_CONTEXT.get()
        record.agent_id = AGENT_ID_CONTEXT.get()
        record.job_id = JOB_ID_CONTEXT.get()
        record.codex_thread_id = CODEX_THREAD_ID_CONTEXT.get()
        record.event_type = EVENT_TYPE_CONTEXT.get()
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
            fmt=(
                "%(asctime)s %(levelname)s %(name)s "
                "request_id=%(request_id)s "
                "session_id=%(session_id)s "
                "agent_id=%(agent_id)s "
                "job_id=%(job_id)s "
                "codex_thread_id=%(codex_thread_id)s "
                "event_type=%(event_type)s "
                "%(message)s"
            )
        )
    )
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured to work with the global logging setup."""
    return logging.getLogger(name)
