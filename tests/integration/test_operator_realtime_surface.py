from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.messages import MessageRecord, MessageRepository
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.runtime_pools import (
    RuntimePoolRecord,
    RuntimePoolRepository,
    WorkContextRecord,
    WorkContextRepository,
)
from app.repositories.session_events import SessionEventRecord, SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_realtime.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_session(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id="ses_live",
                title="Realtime Session",
                goal="Exercise the live operator surface",
                status="active",
                lead_agent_id="agt_planner",
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=now,
                template_key="planning_heavy",
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_agent(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id="agt_planner",
                display_name="Planner",
                role="planner",
                is_lead_default=1,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_phase(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        PhaseRepository(database_url).create(
            PhaseRecord(
                id="ph_live",
                session_id="ses_live",
                phase_key="planning",
                title="Planning",
                description="Plan the realtime surface",
                relay_template_key="planning_template",
                default_channel_key="general",
                sort_order=10,
                is_default=1,
                created_at=now,
                updated_at=now,
            )
        )
    )
    asyncio.run(
        SessionRepository(database_url).update(
            SessionRecord(
                id="ses_live",
                title="Realtime Session",
                goal="Exercise the live operator surface",
                status="active",
                lead_agent_id="agt_planner",
                active_phase_id="ph_live",
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=now,
                template_key="planning_heavy",
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_runtime_pool(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        RuntimePoolRepository(database_url).create(
            RuntimePoolRecord(
                id="rp_live",
                pool_key="local_shell",
                title="Local shell pool",
                description="Pool used for the operator surface",
                runtime_kind="codex",
                preferred_transport_kind=None,
                required_capabilities_json=None,
                fallback_pool_key=None,
                max_active_contexts=1,
                default_isolation_mode="shared",
                pool_status="offline",
                metadata_json=None,
                is_default=1,
                sort_order=10,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_job(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id="job_live",
                session_id="ses_live",
                channel_key="general",
                assigned_agent_id="agt_planner",
                runtime_id=None,
                source_message_id="msg_live",
                parent_job_id=None,
                title="Build realtime shell",
                instructions="Implement live activity streaming.",
                status="paused_by_loop_guard",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="paused",
                result_summary=None,
                error_code="loop_guard",
                error_message="Loop guard stopped the relay",
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_message(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        MessageRepository(database_url).create(
            MessageRecord(
                id="msg_live",
                session_id="ses_live",
                channel_key="general",
                sender_type="agent",
                sender_id="agt_planner",
                message_type="chat",
                content="Streaming is ready.",
                content_format="plain_text",
                reply_to_message_id=None,
                source_message_id=None,
                visibility="session",
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_approval(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id="apr_live",
                job_id="job_live",
                agent_id="agt_planner",
                approval_type="custom",
                status="pending",
                request_payload_json='{"scope":"realtime"}',
                decision_payload_json=None,
                requested_at=now,
                resolved_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_work_context(database_url: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        WorkContextRepository(database_url).create(
            WorkContextRecord(
                id="ctx_live",
                session_id="ses_live",
                job_id="job_live",
                agent_id="agt_planner",
                runtime_pool_id="rp_live",
                runtime_id=None,
                context_key="local_shell:job_live",
                workspace_path=None,
                isolation_mode="shared",
                context_status="active",
                ownership_state="borrowed",
                selection_reason="realtime smoke test",
                failure_reason=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_event_sources(database_url: str) -> None:
    session_events = SessionEventRepository(database_url)
    job_events = JobEventRepository(database_url)
    asyncio.run(
        session_events.create(
            SessionEventRecord(
                id="sev_1",
                session_id="ses_live",
                event_type="message.created",
                actor_type="agent",
                actor_id="agt_planner",
                event_payload_json='{"message_id":"msg_live","sender_type":"agent","sender_id":"agt_planner","channel_key":"general"}',
                created_at="2026-04-01T00:00:01Z",
            )
        )
    )
    asyncio.run(
        session_events.create(
            SessionEventRecord(
                id="sev_2",
                session_id="ses_live",
                event_type="approval.required",
                actor_type="agent",
                actor_id="agt_planner",
                event_payload_json='{"approval_id":"apr_live","job_id":"job_live","agent_id":"agt_planner"}',
                created_at="2026-04-01T00:00:02Z",
            )
        )
    )
    asyncio.run(
        session_events.create(
            SessionEventRecord(
                id="sev_3",
                session_id="ses_live",
                event_type="review.requested",
                actor_type="agent",
                actor_id="agt_planner",
                event_payload_json='{"review_id":"rev_live","job_id":"job_live"}',
                created_at="2026-04-01T00:00:03Z",
            )
        )
    )
    asyncio.run(
        session_events.create(
            SessionEventRecord(
                id="sev_4",
                session_id="ses_live",
                event_type="loop_guard_triggered",
                actor_type="system",
                actor_id=None,
                event_payload_json='{"reason":"loop guard stopped the relay"}',
                created_at="2026-04-01T00:00:04Z",
            )
        )
    )
    asyncio.run(
        job_events.create(
            JobEventRecord(
                id="jev_1",
                job_id="job_live",
                session_id="ses_live",
                event_type="turn.started",
                event_payload_json='{"turn_id":"turn_live"}',
                created_at="2026-04-01T00:00:05Z",
            )
        )
    )
    asyncio.run(
        job_events.create(
            JobEventRecord(
                id="jev_2",
                job_id="job_live",
                session_id="ses_live",
                event_type="command.interrupt",
                event_payload_json='{"reason":"manual stop"}',
                created_at="2026-04-01T00:00:06Z",
            )
        )
    )


def test_operator_realtime_surface_replays_and_cursors(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url)
    _seed_session(database_url)
    _seed_phase(database_url)
    _seed_runtime_pool(database_url)
    _seed_message(database_url)
    _seed_job(database_url)
    _seed_approval(database_url)
    _seed_work_context(database_url)
    _seed_event_sources(database_url)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/operator/sessions/ses_live/activity",
                params={"since_sequence": 0, "limit": 3},
            )
            assert response.status_code == 200
            payload = response.json()

            assert payload["session_id"] == "ses_live"
            assert payload["since_sequence"] == 0
            assert payload["total_events"] >= 6
            assert len(payload["events"]) == 3
            assert payload["events"] == sorted(payload["events"], key=lambda item: item["sequence"])
            assert payload["next_cursor_sequence"] == payload["events"][-1]["sequence"]
            assert payload["signals"]["pending_approvals"]
            assert payload["signals"]["stuck_jobs"]
            assert payload["signals"]["recent_errors"]
            assert payload["signals"]["phase_bottlenecks"]
            assert payload["signals"]["runtime_health"]

            cursor = payload["next_cursor_sequence"]
            asyncio.run(
                SessionEventRepository(database_url).create(
                    SessionEventRecord(
                        id="sev_5",
                        session_id="ses_live",
                        event_type="message.created",
                        actor_type="agent",
                        actor_id="agt_planner",
                        event_payload_json='{"message_id":"msg_live_2","sender_type":"agent","sender_id":"agt_planner","channel_key":"general"}',
                        created_at="2026-04-01T00:00:07Z",
                    )
                )
            )

            replay_response = client.get(
                "/api/v1/operator/sessions/ses_live/activity",
                params={"since_sequence": cursor, "limit": 25},
            )
            assert replay_response.status_code == 200
            replay_payload = replay_response.json()

            assert replay_payload["since_sequence"] == cursor
            assert replay_payload["events"]
            assert replay_payload["events"][0]["sequence"] == cursor + 1
            assert (
                replay_payload["next_cursor_sequence"] == replay_payload["events"][-1]["sequence"]
            )
    finally:
        app_main.get_config.cache_clear()
