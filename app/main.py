"""Application entry point."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router
from app.api.dependencies import get_thread_mapping_store
from app.codex_bridge import create_codex_bridge_client
from app.core.config import AppConfig, get_config
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.version import APP_VERSION
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.artifacts import ArtifactRepository
from app.repositories.jobs import JobEventRepository, JobRepository
from app.repositories.messages import MessageRepository
from app.repositories.presence import PresenceRepository
from app.repositories.relay_edges import RelayEdgeRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.approval_manager import ApprovalManager
from app.services.artifact_manager import ArtifactManager
from app.services.durable_runtime import DurableRuntimeSupervisor
from app.services.loop_guard import LoopGuardService
from app.services.recovery import RecoveryService
from app.services.relay_engine import CodexRelayBridge, RelayEngine
from app.services.runtime_service import RuntimeService
from app.services.thread_mapping import ThreadMappingService

APP_NAME = "codex-collaboration-coordinator"

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def _build_durable_runtime_supervisor(
    settings: AppConfig,
) -> tuple[
    DurableRuntimeSupervisor,
    CodexRelayBridge,
]:
    database_url = settings.database_url
    await migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)
    runtime_repository = AgentRuntimeRepository(database_url)
    job_repository = JobRepository(database_url)
    job_event_repository = JobEventRepository(database_url)
    relay_edge_repository = RelayEdgeRepository(database_url)
    message_repository = MessageRepository(database_url)
    session_repository = SessionRepository(database_url)
    session_event_repository = SessionEventRepository(database_url)
    agent_repository = AgentRepository(database_url)
    artifact_repository = ArtifactRepository(database_url)
    approval_repository = ApprovalRepository(database_url)
    runtime_service = RuntimeService(runtime_repository)
    thread_mapping_service = ThreadMappingService(
        runtime_service,
        store=get_thread_mapping_store(),
    )
    bridge = create_codex_bridge_client(settings.codex_bridge_mode)
    loop_guard_service = LoopGuardService(
        relay_edge_repository=relay_edge_repository,
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
    )
    artifact_manager = ArtifactManager(
        artifact_repository=artifact_repository,
        job_event_repository=job_event_repository,
    )
    approval_manager = ApprovalManager(
        approval_repository=approval_repository,
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        session_event_repository=session_event_repository,
    )
    relay_engine = RelayEngine(
        job_repository=job_repository,
        job_event_repository=job_event_repository,
        relay_edge_repository=relay_edge_repository,
        message_repository=message_repository,
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        agent_repository=agent_repository,
        runtime_service=runtime_service,
        thread_mapping_service=thread_mapping_service,
        loop_guard_service=loop_guard_service,
        artifact_manager=artifact_manager,
        approval_manager=approval_manager,
        bridge=bridge,
    )
    recovery_service = RecoveryService(
        job_repository=job_repository,
        runtime_repository=runtime_repository,
        presence_repository=PresenceRepository(database_url),
        session_repository=session_repository,
        session_event_repository=session_event_repository,
        runtime_service=runtime_service,
        thread_mapping_store=get_thread_mapping_store(),
        relay_engine=relay_engine if settings.runtime_recovery_enabled else None,
        stale_after_minutes=settings.runtime_stale_after_minutes,
    )
    supervisor = DurableRuntimeSupervisor(
        recovery_service=recovery_service,
        enabled=settings.runtime_recovery_enabled,
        poll_interval_seconds=settings.runtime_recovery_interval_seconds,
    )
    try:
        await supervisor.run_once()
    except Exception:
        await bridge.aclose()
        raise
    return supervisor, bridge


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_config()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        supervisor, bridge = await _build_durable_runtime_supervisor(settings)
        _app.state.durable_runtime_supervisor = supervisor
        _app.state.codex_bridge_client = bridge
        await supervisor.start()
        yield
        await supervisor.stop()
        await bridge.aclose()

    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware, header_name=settings.request_id_header)
    install_error_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
