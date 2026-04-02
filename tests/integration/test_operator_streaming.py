from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobRecord, JobRepository
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
    return f"sqlite:///{(tmp_path / 'operator_streaming.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_base_state(database_url: str) -> None:
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
    asyncio.run(
        SessionEventRepository(database_url).create(
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


def test_operator_activity_stream_reconnects_with_last_event_id(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_base_state(database_url)

    try:
        with TestClient(app) as client:
            bootstrap = client.get(
                "/api/v1/operator/sessions/ses_live/activity",
                params={"since_sequence": 0, "limit": 3},
            )
            assert bootstrap.status_code == 200
            cursor = bootstrap.json()["next_cursor_sequence"]

            asyncio.run(
                SessionEventRepository(database_url).create(
                    SessionEventRecord(
                        id="sev_2",
                        session_id="ses_live",
                        event_type="message.created",
                        actor_type="agent",
                        actor_id="agt_planner",
                        event_payload_json='{"message_id":"msg_live_2","sender_type":"agent","sender_id":"agt_planner","channel_key":"general"}',
                        created_at="2026-04-01T00:00:02Z",
                    )
                )
            )

            with client.stream(
                "GET",
                "/api/v1/operator/sessions/ses_live/activity/stream",
                params={"since_sequence": 0, "limit": 25},
                headers={"Last-Event-ID": str(cursor)},
            ) as stream_response:
                assert stream_response.status_code == 200
                assert stream_response.headers["content-type"].startswith("text/event-stream")
                frame = next(stream_response.iter_text())
                assert "event: operator.activity" in frame
                assert f'"next_cursor_sequence": {cursor + 1}' in frame
                assert '"event_type": "message.created"' in frame
    finally:
        app_main.get_config.cache_clear()
