from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import MessageRecord, MessageRepository
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.reviews import ReviewRecord, ReviewRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.repositories.transcript_exports import (
    TranscriptExportRecord,
    TranscriptExportRepository,
)


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_ui_shell.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(database_url: str, *, agent_id: str, display_name: str, role: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=display_name,
                role=role,
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_session(
    database_url: str,
    *,
    session_id: str,
    title: str,
    active_phase_id: str | None,
    template_key: str | None,
) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title=title,
                goal=f"Goal for {title}",
                status="active",
                lead_agent_id="agt_planner",
                active_phase_id=active_phase_id,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=now,
                template_key=template_key,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_phase(
    database_url: str,
    *,
    phase_id: str,
    session_id: str,
    phase_key: str,
    is_default: int = 0,
) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        PhaseRepository(database_url).create(
            PhaseRecord(
                id=phase_id,
                session_id=session_id,
                phase_key=phase_key,
                title=phase_key.title(),
                description=None,
                relay_template_key=f"{phase_key}_template",
                default_channel_key="general",
                sort_order=10,
                is_default=is_default,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_participant(database_url: str, *, session_id: str, agent_id: str, role: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        ParticipantRepository(database_url).create(
            SessionParticipantRecord(
                id=f"sp_{session_id}_{agent_id}",
                session_id=session_id,
                agent_id=agent_id,
                runtime_id=None,
                is_lead=1 if role == "planner" else 0,
                read_scope="shared_history",
                write_scope="mention_or_direct_assignment",
                participant_status="joined",
                joined_at=now,
                left_at=None,
                created_at=now,
                updated_at=now,
                role=role,
                policy_json=None,
            )
        )
    )


def _seed_message(database_url: str, *, session_id: str, sender_id: str) -> str:
    now = "2026-04-01T00:00:00Z"
    message_id = f"msg_{session_id}"
    asyncio.run(
        MessageRepository(database_url).create(
            MessageRecord(
                id=message_id,
                session_id=session_id,
                channel_key="general",
                sender_type="agent",
                sender_id=sender_id,
                message_type="chat",
                content="Ship the operator shell",
                content_format="plain_text",
                reply_to_message_id=None,
                source_message_id=None,
                visibility="session",
                created_at=now,
                updated_at=now,
            )
        )
    )
    return message_id


def _seed_job(database_url: str, *, session_id: str, agent_id: str) -> str:
    now = "2026-04-01T00:00:00Z"
    job_id = f"job_{session_id}"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Build operator shell",
                instructions="Render the thin operator shell",
                status="queued",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="queued",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )
    return job_id


def _seed_approval(database_url: str, *, job_id: str, agent_id: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=f"apr_{job_id}",
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"scope":"shell"}',
                decision_payload_json=None,
                requested_at=now,
                resolved_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_review(database_url: str, *, session_id: str, job_id: str, agent_id: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        ReviewRepository(database_url).create(
            ReviewRecord(
                id=f"rev_{job_id}",
                session_id=session_id,
                source_job_id=job_id,
                reviewer_agent_id=agent_id,
                requested_by_agent_id="agt_planner",
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
                requested_at=now,
                decided_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_artifact(database_url: str, *, session_id: str, job_id: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        ArtifactRepository(database_url).create(
            ArtifactRecord(
                id=f"art_{session_id}",
                job_id=job_id,
                session_id=session_id,
                channel_key="general",
                source_message_id=None,
                artifact_type="json",
                title="Operator shell note",
                content_text="The shell can load transcript, jobs, approvals, and artifacts.",
                file_path=None,
                file_name=None,
                mime_type=None,
                size_bytes=None,
                checksum_sha256=None,
                metadata_json='{"surface":"operator"}',
                created_at=now,
                updated_at=now,
            )
        )
    )


def _seed_transcript_export(database_url: str, *, session_id: str) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        TranscriptExportRepository(database_url).create(
            TranscriptExportRecord(
                id=f"tex_{session_id}",
                session_id=session_id,
                export_kind="transcript",
                export_format="text",
                title="Shell transcript",
                file_name=f"{session_id}.md",
                mime_type="text/markdown",
                content_text="# Operator Shell\nLoaded successfully.",
                size_bytes=34,
                checksum_sha256="abc123",
                metadata_json='{"generated_by":"test"}',
                created_at=now,
                updated_at=now,
            )
        )
    )


def test_operator_shell_bootstrap_and_page(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_planner", display_name="Planner", role="planner")
    _seed_session(
        database_url,
        session_id="ses_other",
        title="Other Session",
        active_phase_id=None,
        template_key="implementation_review",
    )
    _seed_session(
        database_url,
        session_id="ses_focus",
        title="Focused Session",
        active_phase_id="ph_focus",
        template_key="planning_heavy",
    )
    _seed_phase(
        database_url,
        phase_id="ph_focus",
        session_id="ses_focus",
        phase_key="planning",
        is_default=1,
    )
    _seed_participant(database_url, session_id="ses_focus", agent_id="agt_planner", role="planner")
    _seed_message(database_url, session_id="ses_focus", sender_id="agt_planner")
    job_id = _seed_job(database_url, session_id="ses_focus", agent_id="agt_planner")
    _seed_review(database_url, session_id="ses_focus", job_id=job_id, agent_id="agt_planner")
    _seed_approval(database_url, job_id=job_id, agent_id="agt_planner")
    _seed_artifact(database_url, session_id="ses_focus", job_id=job_id)
    _seed_transcript_export(database_url, session_id="ses_focus")

    try:
        with TestClient(app) as client:
            page_response = client.get("/operator")
            assert page_response.status_code == 200
            assert "Operator Shell" in page_response.text
            assert "/api/v1/operator/shell" in page_response.text

            bootstrap_response = client.get(
                "/api/v1/operator/shell",
                params={"session_id": "ses_focus"},
            )
            assert bootstrap_response.status_code == 200
            payload = bootstrap_response.json()

            assert payload["selected_session_id"] == "ses_focus"
            assert len(payload["sessions"]) == 2
            selected = payload["selected_session"]
            assert selected["session"]["id"] == "ses_focus"
            assert selected["message_count"] == 1
            assert selected["job_count"] == 1
            assert selected["approval_count"] == 1
            assert selected["artifact_count"] == 1
            assert len(selected["participants"]) == 1
            assert len(selected["messages"]) == 1
            assert len(selected["jobs"]) == 1
            assert len(selected["approvals"]) == 1
            assert len(selected["artifacts"]) == 1
            assert len(selected["transcript_exports"]) == 1
            assert payload["dashboard"]["filters"]["session_id"] == "ses_focus"
    finally:
        app_main.get_config.cache_clear()
