from __future__ import annotations

import asyncio
import logging
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.core.logging import RequestIdFilter
from app.core.telemetry import reset_telemetry_service
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.a2a_tasks import A2ATaskRecord, A2ATaskRepository
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.orchestration_runs import (
    OrchestrationRunRecord,
    OrchestrationRunRepository,
)
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.reviews import ReviewRecord, ReviewRepository
from app.repositories.runtime_pools import WorkContextRecord, WorkContextRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'telemetry.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent_and_runtime(
    database_url: str,
    *,
    agent_id: str,
    runtime_id: str,
    runtime_status: str = "online",
    heartbeat_at: str | None = "2026-04-01T00:00:00Z",
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=agent_id,
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )
    asyncio.run(
        AgentRuntimeRepository(database_url).create(
            AgentRuntimeRecord(
                id=runtime_id,
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status=runtime_status,
                last_heartbeat_at=heartbeat_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str, title: str, active_phase_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title=title,
                goal="Telemetry test",
                status="active",
                lead_agent_id="agt_lead",
                active_phase_id=active_phase_id,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_phase(
    database_url: str,
    *,
    phase_id: str,
    session_id: str,
    phase_key: str,
    relay_template_key: str,
    sort_order: int,
    is_default: int = 0,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        PhaseRepository(database_url).create(
            PhaseRecord(
                id=phase_id,
                session_id=session_id,
                phase_key=phase_key,
                title=phase_key.title(),
                description=None,
                relay_template_key=relay_template_key,
                default_channel_key="general",
                sort_order=sort_order,
                is_default=is_default,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    status: str,
    thread_id: str,
    runtime_id: str | None = None,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=runtime_id,
                source_message_id=None,
                parent_job_id=None,
                title=f"Job {job_id}",
                instructions="Telemetry test",
                status=status,
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=thread_id,
                active_turn_id=f"turn_{job_id}",
                last_known_turn_status=status,
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=created_at if status != "queued" else None,
                completed_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_review(
    database_url: str,
    *,
    review_id: str,
    session_id: str,
    source_job_id: str,
    reviewer_agent_id: str,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        ReviewRepository(database_url).create(
            ReviewRecord(
                id=review_id,
                session_id=session_id,
                source_job_id=source_job_id,
                reviewer_agent_id=reviewer_agent_id,
                requested_by_agent_id="agt_lead",
                review_scope="job",
                review_status="requested",
                review_channel_key="review",
                template_key="builder_to_reviewer",
                request_message_id=None,
                decision_message_id=None,
                summary_artifact_id=None,
                revision_job_id=None,
                request_payload_json='{"scope":"job"}',
                decision_payload_json=None,
                requested_at=created_at,
                decided_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_context(
    database_url: str,
    *,
    context_id: str,
    session_id: str,
    job_id: str,
    agent_id: str,
    runtime_pool_id: str,
    runtime_id: str,
    context_status: str,
    ownership_state: str,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        WorkContextRepository(database_url).create(
            WorkContextRecord(
                id=context_id,
                session_id=session_id,
                job_id=job_id,
                agent_id=agent_id,
                runtime_pool_id=runtime_pool_id,
                runtime_id=runtime_id,
                context_key=f"{context_id}_key",
                workspace_path="/workspace/project",
                isolation_mode="isolated" if runtime_pool_id == "rpl_isolated_work" else "shared",
                context_status=context_status,
                ownership_state=ownership_state,
                selection_reason="telemetry test",
                failure_reason=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_task(
    database_url: str,
    *,
    task_id: str,
    session_id: str,
    job_id: str,
    phase_id: str,
    context_id: str,
    task_status: str,
    relay_template_key: str,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        A2ATaskRepository(database_url).create(
            A2ATaskRecord(
                id=f"task_{task_id}",
                session_id=session_id,
                job_id=job_id,
                phase_id=phase_id,
                task_id=task_id,
                context_id=context_id,
                task_status=task_status,
                relay_template_key=relay_template_key,
                primary_artifact_id=None,
                task_payload_json='{"kind":"public"}',
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_approval(database_url: str, *, approval_id: str, job_id: str, agent_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"command":"pytest"}',
                decision_payload_json=None,
                requested_at=created_at,
                resolved_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_run(
    database_url: str,
    *,
    run_id: str,
    session_id: str,
    current_phase_key: str,
    source_job_id: str,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        OrchestrationRunRepository(database_url).create(
            OrchestrationRunRecord(
                id=run_id,
                session_id=session_id,
                status="blocked",
                current_phase_id=None,
                current_phase_key=current_phase_key,
                pending_phase_key="finalize",
                failure_phase_key="revise",
                gate_type="review_required",
                gate_status="pending",
                source_job_id=source_job_id,
                handoff_job_id=None,
                review_id=None,
                approval_id=None,
                transition_artifact_id=None,
                decision_artifact_id=None,
                revision_job_id=None,
                requested_by_agent_id="agt_lead",
                transition_reason="Needs review",
                started_at=created_at,
                decided_at=None,
                completed_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def test_telemetry_surface_and_correlation(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    reset_telemetry_service()
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent_and_runtime(database_url, agent_id="agt_lead", runtime_id="rt_lead")
    _seed_agent_and_runtime(database_url, agent_id="agt_builder", runtime_id="rt_builder")
    _seed_agent_and_runtime(
        database_url,
        agent_id="agt_reviewer",
        runtime_id="rt_reviewer",
        runtime_status="busy",
    )
    _seed_session(
        database_url,
        session_id="ses_plan",
        title="Planning Session",
        active_phase_id="ph_plan",
    )
    _seed_session(
        database_url,
        session_id="ses_review",
        title="Review Session",
        active_phase_id="ph_review",
    )
    _seed_phase(
        database_url,
        phase_id="ph_plan",
        session_id="ses_plan",
        phase_key="planning",
        relay_template_key="planner_to_builder",
        sort_order=10,
        is_default=1,
    )
    _seed_phase(
        database_url,
        phase_id="ph_review",
        session_id="ses_review",
        phase_key="review",
        relay_template_key="builder_to_reviewer",
        sort_order=10,
        is_default=1,
    )
    _seed_job(
        database_url,
        job_id="job_queued",
        session_id="ses_plan",
        agent_id="agt_builder",
        status="queued",
        runtime_id="rt_builder",
        thread_id="thr_q",
    )
    _seed_job(
        database_url,
        job_id="job_running",
        session_id="ses_review",
        agent_id="agt_reviewer",
        status="input_required",
        runtime_id="rt_reviewer",
        thread_id="thr_r",
    )
    _seed_review(
        database_url,
        review_id="rev_1",
        session_id="ses_review",
        source_job_id="job_running",
        reviewer_agent_id="agt_reviewer",
    )
    _seed_approval(database_url, approval_id="apr_1", job_id="job_running", agent_id="agt_reviewer")
    _seed_run(
        database_url,
        run_id="run_1",
        session_id="ses_review",
        current_phase_key="review",
        source_job_id="job_running",
    )
    _seed_context(
        database_url,
        context_id="ctx_plan",
        session_id="ses_plan",
        job_id="job_queued",
        agent_id="agt_builder",
        runtime_pool_id="rpl_general_shared",
        runtime_id="rt_builder",
        context_status="active",
        ownership_state="owned",
    )
    _seed_context(
        database_url,
        context_id="ctx_review",
        session_id="ses_review",
        job_id="job_running",
        agent_id="agt_reviewer",
        runtime_pool_id="rpl_isolated_work",
        runtime_id="rt_reviewer",
        context_status="waiting_for_runtime",
        ownership_state="borrowed",
    )
    _seed_task(
        database_url,
        task_id="task_plan",
        session_id="ses_plan",
        job_id="job_queued",
        phase_id="ph_plan",
        context_id="ctx_plan",
        task_status="queued",
        relay_template_key="planner_to_builder",
    )
    _seed_task(
        database_url,
        task_id="task_review",
        session_id="ses_review",
        job_id="job_running",
        phase_id="ph_review",
        context_id="ctx_review",
        task_status="completed",
        relay_template_key="builder_to_reviewer",
    )

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        logging.Formatter("%(request_id)s %(request_method)s %(request_path)s %(message)s")
    )
    handler.addFilter(RequestIdFilter())
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        with TestClient(app) as client:
            status_response = client.get(
                "/api/v1/system/status",
                headers={"X-Request-ID": "req-telemetry"},
            )
            assert status_response.status_code == 200
            status_payload = status_response.json()
            assert status_payload["telemetry"]["sample_counts"]["system_status"] >= 1
            assert status_payload["telemetry"]["summary"]["queue_depth"] >= 1
            assert status_payload["telemetry"]["summary"]["average_job_latency_seconds"] is not None
            assert (
                status_payload["telemetry"]["summary"]["average_phase_duration_seconds"] is not None
            )
            assert status_payload["telemetry"]["summary"]["pending_review_bottlenecks"] >= 1

            debug_response = client.get("/api/v1/system/debug")
            assert debug_response.status_code == 200
            debug_payload = debug_response.json()
            assert debug_payload["telemetry"]["sample_counts"]["debug_surface"] >= 1
            assert debug_payload["telemetry"]["summary"]["queue_depth"] >= 1
            assert debug_payload["telemetry"]["summary"]["pending_review_bottlenecks"] >= 1

            dashboard_response = client.get("/api/v1/operator/dashboard")
            assert dashboard_response.status_code == 200
            dashboard_payload = dashboard_response.json()
            assert dashboard_payload["telemetry"]["sample_counts"]["operator_dashboard"] >= 1
            assert (
                dashboard_payload["telemetry"]["summary"]["public_task_throughput"]["total_tasks"]
                == 2
            )
            assert (
                dashboard_payload["telemetry"]["summary"]["runtime_pool_pressure"]["isolated_work"][
                    "blocked_jobs"
                ]
                == 1
            )

            log_output = stream.getvalue()
            assert "req-telemetry GET /api/v1/system/status" in log_output
    finally:
        root_logger.removeHandler(handler)
        app_main.get_config.cache_clear()
