"""Application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router
from app.api.dependencies import get_thread_mapping_store
from app.core.config import AppConfig, get_config
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRuntimeRepository
from app.repositories.jobs import JobRepository
from app.repositories.presence import PresenceRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.recovery import RecoveryService
from app.services.runtime_service import RuntimeService

APP_NAME = "codex-collaboration-coordinator"
APP_VERSION = "0.1.0"


async def _recover_state(settings: AppConfig) -> None:
    database_url = settings.database_url
    await migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)
    runtime_repository = AgentRuntimeRepository(database_url)
    recovery_service = RecoveryService(
        job_repository=JobRepository(database_url),
        runtime_repository=runtime_repository,
        presence_repository=PresenceRepository(database_url),
        session_repository=SessionRepository(database_url),
        session_event_repository=SessionEventRepository(database_url),
        runtime_service=RuntimeService(runtime_repository),
        thread_mapping_store=get_thread_mapping_store(),
    )
    await recovery_service.recover()


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_config()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await _recover_state(settings)
        yield

    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware, header_name=settings.request_id_header)
    install_error_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
