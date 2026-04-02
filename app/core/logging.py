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
REQUEST_METHOD_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_method",
    default=LOG_CONTEXT_DEFAULT,
)
REQUEST_PATH_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_path",
    default=LOG_CONTEXT_DEFAULT,
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
PHASE_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "phase_id",
    default=LOG_CONTEXT_DEFAULT,
)
REVIEW_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "review_id",
    default=LOG_CONTEXT_DEFAULT,
)
RUNTIME_POOL_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "runtime_pool_id",
    default=LOG_CONTEXT_DEFAULT,
)
RUNTIME_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "runtime_id",
    default=LOG_CONTEXT_DEFAULT,
)
CODEX_THREAD_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "codex_thread_id",
    default=LOG_CONTEXT_DEFAULT,
)
TASK_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "task_id",
    default=LOG_CONTEXT_DEFAULT,
)
SUBSCRIPTION_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "subscription_id",
    default=LOG_CONTEXT_DEFAULT,
)
EVENT_TYPE_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "event_type",
    default=LOG_CONTEXT_DEFAULT,
)
ACCESS_MODE_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "access_mode",
    default=LOG_CONTEXT_DEFAULT,
)
ACCESS_SURFACE_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "access_surface",
    default=LOG_CONTEXT_DEFAULT,
)
ACCESS_RESULT_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "access_result",
    default=LOG_CONTEXT_DEFAULT,
)
ACCESS_REASON_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "access_reason",
    default=LOG_CONTEXT_DEFAULT,
)
PRINCIPAL_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "principal_id",
    default=LOG_CONTEXT_DEFAULT,
)
CREDENTIAL_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "credential_id",
    default=LOG_CONTEXT_DEFAULT,
)
CLIENT_HOST_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "client_host",
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


def get_log_context() -> dict[str, str]:
    """Snapshot the active logging context into a plain dictionary."""
    return {
        "request_id": REQUEST_ID_CONTEXT.get(),
        "request_method": REQUEST_METHOD_CONTEXT.get(),
        "request_path": REQUEST_PATH_CONTEXT.get(),
        "session_id": SESSION_ID_CONTEXT.get(),
        "agent_id": AGENT_ID_CONTEXT.get(),
        "job_id": JOB_ID_CONTEXT.get(),
        "phase_id": PHASE_ID_CONTEXT.get(),
        "review_id": REVIEW_ID_CONTEXT.get(),
        "runtime_pool_id": RUNTIME_POOL_ID_CONTEXT.get(),
        "runtime_id": RUNTIME_ID_CONTEXT.get(),
        "codex_thread_id": CODEX_THREAD_ID_CONTEXT.get(),
        "task_id": TASK_ID_CONTEXT.get(),
        "subscription_id": SUBSCRIPTION_ID_CONTEXT.get(),
        "event_type": EVENT_TYPE_CONTEXT.get(),
        "access_mode": ACCESS_MODE_CONTEXT.get(),
        "access_surface": ACCESS_SURFACE_CONTEXT.get(),
        "access_result": ACCESS_RESULT_CONTEXT.get(),
        "access_reason": ACCESS_REASON_CONTEXT.get(),
        "principal_id": PRINCIPAL_ID_CONTEXT.get(),
        "credential_id": CREDENTIAL_ID_CONTEXT.get(),
        "client_host": CLIENT_HOST_CONTEXT.get(),
    }


def bind_log_context(
    *,
    request_method: str | None = None,
    request_path: str | None = None,
    session_id: str | None = None,
    agent_id: str | None = None,
    job_id: str | None = None,
    phase_id: str | None = None,
    review_id: str | None = None,
    runtime_pool_id: str | None = None,
    runtime_id: str | None = None,
    codex_thread_id: str | None = None,
    task_id: str | None = None,
    subscription_id: str | None = None,
    event_type: str | None = None,
    access_mode: str | None = None,
    access_surface: str | None = None,
    access_result: str | None = None,
    access_reason: str | None = None,
    principal_id: str | None = None,
    credential_id: str | None = None,
    client_host: str | None = None,
) -> dict[str, contextvars.Token[str]]:
    """Bind operator-relevant logging fields into the current context."""
    tokens: dict[str, contextvars.Token[str]] = {}
    if request_method is not None:
        tokens["request_method"] = REQUEST_METHOD_CONTEXT.set(request_method)
    if request_path is not None:
        tokens["request_path"] = REQUEST_PATH_CONTEXT.set(request_path)
    if session_id is not None:
        tokens["session_id"] = SESSION_ID_CONTEXT.set(session_id)
    if agent_id is not None:
        tokens["agent_id"] = AGENT_ID_CONTEXT.set(agent_id)
    if job_id is not None:
        tokens["job_id"] = JOB_ID_CONTEXT.set(job_id)
    if phase_id is not None:
        tokens["phase_id"] = PHASE_ID_CONTEXT.set(phase_id)
    if review_id is not None:
        tokens["review_id"] = REVIEW_ID_CONTEXT.set(review_id)
    if runtime_pool_id is not None:
        tokens["runtime_pool_id"] = RUNTIME_POOL_ID_CONTEXT.set(runtime_pool_id)
    if runtime_id is not None:
        tokens["runtime_id"] = RUNTIME_ID_CONTEXT.set(runtime_id)
    if codex_thread_id is not None:
        tokens["codex_thread_id"] = CODEX_THREAD_ID_CONTEXT.set(codex_thread_id)
    if task_id is not None:
        tokens["task_id"] = TASK_ID_CONTEXT.set(task_id)
    if subscription_id is not None:
        tokens["subscription_id"] = SUBSCRIPTION_ID_CONTEXT.set(subscription_id)
    if event_type is not None:
        tokens["event_type"] = EVENT_TYPE_CONTEXT.set(event_type)
    if access_mode is not None:
        tokens["access_mode"] = ACCESS_MODE_CONTEXT.set(access_mode)
    if access_surface is not None:
        tokens["access_surface"] = ACCESS_SURFACE_CONTEXT.set(access_surface)
    if access_result is not None:
        tokens["access_result"] = ACCESS_RESULT_CONTEXT.set(access_result)
    if access_reason is not None:
        tokens["access_reason"] = ACCESS_REASON_CONTEXT.set(access_reason)
    if principal_id is not None:
        tokens["principal_id"] = PRINCIPAL_ID_CONTEXT.set(principal_id)
    if credential_id is not None:
        tokens["credential_id"] = CREDENTIAL_ID_CONTEXT.set(credential_id)
    if client_host is not None:
        tokens["client_host"] = CLIENT_HOST_CONTEXT.set(client_host)
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
        elif key == "phase_id":
            PHASE_ID_CONTEXT.reset(token)
        elif key == "review_id":
            REVIEW_ID_CONTEXT.reset(token)
        elif key == "runtime_pool_id":
            RUNTIME_POOL_ID_CONTEXT.reset(token)
        elif key == "runtime_id":
            RUNTIME_ID_CONTEXT.reset(token)
        elif key == "codex_thread_id":
            CODEX_THREAD_ID_CONTEXT.reset(token)
        elif key == "task_id":
            TASK_ID_CONTEXT.reset(token)
        elif key == "subscription_id":
            SUBSCRIPTION_ID_CONTEXT.reset(token)
        elif key == "event_type":
            EVENT_TYPE_CONTEXT.reset(token)
        elif key == "access_mode":
            ACCESS_MODE_CONTEXT.reset(token)
        elif key == "access_surface":
            ACCESS_SURFACE_CONTEXT.reset(token)
        elif key == "access_result":
            ACCESS_RESULT_CONTEXT.reset(token)
        elif key == "access_reason":
            ACCESS_REASON_CONTEXT.reset(token)
        elif key == "principal_id":
            PRINCIPAL_ID_CONTEXT.reset(token)
        elif key == "credential_id":
            CREDENTIAL_ID_CONTEXT.reset(token)
        elif key == "client_host":
            CLIENT_HOST_CONTEXT.reset(token)
        elif key == "request_method":
            REQUEST_METHOD_CONTEXT.reset(token)
        elif key == "request_path":
            REQUEST_PATH_CONTEXT.reset(token)


def clear_access_context() -> None:
    """Reset access-related logging fields to their defaults."""
    ACCESS_MODE_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    ACCESS_SURFACE_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    ACCESS_RESULT_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    ACCESS_REASON_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    PRINCIPAL_ID_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    CREDENTIAL_ID_CONTEXT.set(LOG_CONTEXT_DEFAULT)
    CLIENT_HOST_CONTEXT.set(LOG_CONTEXT_DEFAULT)


class RequestIdFilter(logging.Filter):
    """Inject the request id into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_log_context()
        record.request_id = context["request_id"]
        record.request_method = context["request_method"]
        record.request_path = context["request_path"]
        record.session_id = context["session_id"]
        record.agent_id = context["agent_id"]
        record.job_id = context["job_id"]
        record.phase_id = context["phase_id"]
        record.review_id = context["review_id"]
        record.runtime_pool_id = context["runtime_pool_id"]
        record.runtime_id = context["runtime_id"]
        record.codex_thread_id = context["codex_thread_id"]
        record.task_id = context["task_id"]
        record.subscription_id = context["subscription_id"]
        record.event_type = context["event_type"]
        record.access_mode = context["access_mode"]
        record.access_surface = context["access_surface"]
        record.access_result = context["access_result"]
        record.access_reason = context["access_reason"]
        record.principal_id = context["principal_id"]
        record.credential_id = context["credential_id"]
        record.client_host = context["client_host"]
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
                "request_method=%(request_method)s "
                "request_path=%(request_path)s "
                "session_id=%(session_id)s "
                "agent_id=%(agent_id)s "
                "job_id=%(job_id)s "
                "phase_id=%(phase_id)s "
                "review_id=%(review_id)s "
                "runtime_pool_id=%(runtime_pool_id)s "
                "runtime_id=%(runtime_id)s "
                "codex_thread_id=%(codex_thread_id)s "
                "task_id=%(task_id)s "
                "subscription_id=%(subscription_id)s "
                "event_type=%(event_type)s "
                "access_mode=%(access_mode)s "
                "access_surface=%(access_surface)s "
                "access_result=%(access_result)s "
                "access_reason=%(access_reason)s "
                "principal_id=%(principal_id)s "
                "credential_id=%(credential_id)s "
                "client_host=%(client_host)s "
                "%(message)s"
            )
        )
    )
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured to work with the global logging setup."""
    return logging.getLogger(name)
