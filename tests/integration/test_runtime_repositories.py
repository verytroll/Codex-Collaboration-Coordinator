from __future__ import annotations

import asyncio
from dataclasses import replace

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.messages import (
    MessageMentionRecord,
    MessageMentionRepository,
    MessageRecord,
    MessageRepository,
)
from app.repositories.presence import PresenceHeartbeatRecord, PresenceRepository
from app.repositories.relay_edges import RelayEdgeRecord, RelayEdgeRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'runtime_repositories.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _bootstrap_session_and_agent(
    database_url: str,
    session_id: str,
    agent_id: str,
) -> tuple[SessionRepository, AgentRepository]:
    session_repository = SessionRepository(database_url)
    agent_repository = AgentRepository(database_url)

    asyncio.run(
        agent_repository.create(
            AgentRecord(
                id=agent_id,
                display_name="Runtime Agent",
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )
    asyncio.run(
        session_repository.create(
            SessionRecord(
                id=session_id,
                title="Runtime session",
                goal=None,
                status="active",
                lead_agent_id=None,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )
    return session_repository, agent_repository


def test_message_and_mention_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository, agent_repository = _bootstrap_session_and_agent(
        database_url,
        "ses_msg",
        "agt_msg",
    )
    message_repository = MessageRepository(database_url)
    mention_repository = MessageMentionRepository(database_url)

    message = MessageRecord(
        id="msg_001",
        session_id="ses_msg",
        sender_type="agent",
        sender_id="agt_msg",
        message_type="chat",
        content="Hello #builder",
        content_format="plain_text",
        reply_to_message_id=None,
        source_message_id=None,
        visibility="session",
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    mention = MessageMentionRecord(
        id="mmt_001",
        message_id=message.id,
        mentioned_agent_id="agt_msg",
        mention_text="#builder",
        mention_order=0,
        created_at="2026-03-31T00:00:00Z",
    )

    created_message = asyncio.run(message_repository.create(message))
    created_mention = asyncio.run(mention_repository.create(mention))
    fetched_message = asyncio.run(message_repository.get(message.id))
    fetched_mentions = asyncio.run(mention_repository.list_by_message(message.id))
    updated_message = replace(created_message, content="Hello world")

    assert created_message == message
    assert created_mention == mention
    assert fetched_message == message
    assert fetched_mentions == [mention]

    saved_message = asyncio.run(message_repository.update(updated_message))
    listed_messages = asyncio.run(message_repository.list_by_session(message.session_id))
    deleted_mention = asyncio.run(mention_repository.delete(mention.id))
    deleted_message = asyncio.run(message_repository.delete(message.id))

    assert saved_message.content == "Hello world"
    assert len(listed_messages) == 1
    assert deleted_mention is True
    assert deleted_message is True
    assert asyncio.run(mention_repository.get(mention.id)) is None
    assert asyncio.run(message_repository.get(message.id)) is None
    assert asyncio.run(session_repository.delete("ses_msg")) is True
    assert asyncio.run(agent_repository.delete("agt_msg")) is True


def test_job_and_job_event_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository, agent_repository = _bootstrap_session_and_agent(
        database_url,
        "ses_job",
        "agt_job",
    )
    job_repository = JobRepository(database_url)
    job_event_repository = JobEventRepository(database_url)

    job = JobRecord(
        id="job_001",
        session_id="ses_job",
        assigned_agent_id="agt_job",
        runtime_id=None,
        source_message_id=None,
        parent_job_id=None,
        title="Run task",
        instructions="Inspect repository layer",
        status="queued",
        hop_count=0,
        priority="normal",
        codex_runtime_id=None,
        codex_thread_id=None,
        active_turn_id=None,
        last_known_turn_status=None,
        result_summary=None,
        error_code=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    job_event = JobEventRecord(
        id="jbe_001",
        job_id=job.id,
        session_id=job.session_id,
        event_type="created",
        event_payload_json='{"source":"test"}',
        created_at="2026-03-31T00:00:00Z",
    )

    created_job = asyncio.run(job_repository.create(job))
    created_event = asyncio.run(job_event_repository.create(job_event))
    fetched_job = asyncio.run(job_repository.get(job.id))
    fetched_events = asyncio.run(job_event_repository.list_by_job(job.id))
    updated_job = replace(created_job, status="running", started_at="2026-03-31T00:01:00Z")

    assert created_job == job
    assert created_event == job_event
    assert fetched_job == job
    assert fetched_events == [job_event]

    saved_job = asyncio.run(job_repository.update(updated_job))
    listed_jobs = asyncio.run(job_repository.list_by_session(job.session_id))
    deleted_event = asyncio.run(job_event_repository.delete(job_event.id))
    deleted_job = asyncio.run(job_repository.delete(job.id))

    assert saved_job.status == "running"
    assert len(listed_jobs) == 1
    assert deleted_event is True
    assert deleted_job is True
    assert asyncio.run(job_event_repository.get(job_event.id)) is None
    assert asyncio.run(job_repository.get(job.id)) is None
    assert asyncio.run(session_repository.delete("ses_job")) is True
    assert asyncio.run(agent_repository.delete("agt_job")) is True


def test_artifact_and_approval_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository, agent_repository = _bootstrap_session_and_agent(
        database_url,
        "ses_art",
        "agt_art",
    )
    job_repository = JobRepository(database_url)
    artifact_repository = ArtifactRepository(database_url)
    approval_repository = ApprovalRepository(database_url)

    job = JobRecord(
        id="job_art",
        session_id="ses_art",
        assigned_agent_id="agt_art",
        runtime_id=None,
        source_message_id=None,
        parent_job_id=None,
        title="Collect artifact",
        instructions=None,
        status="running",
        hop_count=0,
        priority="normal",
        codex_runtime_id=None,
        codex_thread_id=None,
        active_turn_id=None,
        last_known_turn_status=None,
        result_summary=None,
        error_code=None,
        error_message=None,
        started_at="2026-03-31T00:00:00Z",
        completed_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    artifact = ArtifactRecord(
        id="art_001",
        job_id=job.id,
        session_id=job.session_id,
        source_message_id=None,
        artifact_type="final_text",
        title="Result",
        content_text="Done",
        file_path=None,
        file_name=None,
        mime_type="text/plain",
        size_bytes=4,
        checksum_sha256=None,
        metadata_json='{"kind":"summary"}',
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    approval = ApprovalRequestRecord(
        id="apr_001",
        job_id=job.id,
        agent_id="agt_art",
        approval_type="custom",
        status="pending",
        request_payload_json='{"prompt":"approve"}',
        decision_payload_json=None,
        requested_at="2026-03-31T00:00:00Z",
        resolved_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    asyncio.run(job_repository.create(job))
    created_artifact = asyncio.run(artifact_repository.create(artifact))
    created_approval = asyncio.run(approval_repository.create(approval))
    fetched_artifact = asyncio.run(artifact_repository.get(artifact.id))
    fetched_approvals = asyncio.run(approval_repository.list_by_job(job.id))
    updated_artifact = replace(created_artifact, title="Updated result")
    updated_approval = replace(
        created_approval, status="accepted", resolved_at="2026-03-31T00:05:00Z"
    )

    assert created_artifact == artifact
    assert created_approval == approval
    assert fetched_artifact == artifact
    assert fetched_approvals == [approval]

    saved_artifact = asyncio.run(artifact_repository.update(updated_artifact))
    saved_approval = asyncio.run(approval_repository.update(updated_approval))
    listed_artifacts = asyncio.run(artifact_repository.list_by_job(job.id))
    deleted_artifact = asyncio.run(artifact_repository.delete(artifact.id))
    deleted_approval = asyncio.run(approval_repository.delete(approval.id))

    assert saved_artifact.title == "Updated result"
    assert saved_approval.status == "accepted"
    assert len(listed_artifacts) == 1
    assert deleted_artifact is True
    assert deleted_approval is True
    assert asyncio.run(artifact_repository.get(artifact.id)) is None
    assert asyncio.run(approval_repository.get(approval.id)) is None
    assert asyncio.run(job_repository.delete(job.id)) is True
    assert asyncio.run(session_repository.delete("ses_art")) is True
    assert asyncio.run(agent_repository.delete("agt_art")) is True


def test_presence_and_relay_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository, agent_repository = _bootstrap_session_and_agent(
        database_url,
        "ses_misc",
        "agt_misc",
    )
    presence_repository = PresenceRepository(database_url)
    relay_repository = RelayEdgeRepository(database_url)

    heartbeat = PresenceHeartbeatRecord(
        id="pre_001",
        agent_id="agt_misc",
        runtime_id=None,
        presence="online",
        heartbeat_at="2026-03-31T00:00:00Z",
        details_json='{"source":"test"}',
        created_at="2026-03-31T00:00:00Z",
    )
    edge = RelayEdgeRecord(
        id="rel_001",
        session_id="ses_misc",
        source_message_id=None,
        source_job_id=None,
        target_agent_id="agt_misc",
        target_job_id=None,
        relay_reason="manual_relay",
        hop_number=1,
        created_at="2026-03-31T00:00:00Z",
    )

    created_heartbeat = asyncio.run(presence_repository.create(heartbeat))
    created_edge = asyncio.run(relay_repository.create(edge))
    fetched_heartbeat = asyncio.run(presence_repository.get(heartbeat.id))
    fetched_edges = asyncio.run(relay_repository.list_by_session("ses_misc"))
    updated_heartbeat = replace(created_heartbeat, presence="busy")
    updated_edge = replace(created_edge, hop_number=2)

    assert created_heartbeat == heartbeat
    assert created_edge == edge
    assert fetched_heartbeat == heartbeat
    assert fetched_edges == [edge]

    saved_heartbeat = asyncio.run(presence_repository.update(updated_heartbeat))
    saved_edge = asyncio.run(relay_repository.update(updated_edge))
    listed_heartbeats = asyncio.run(presence_repository.list_by_agent("agt_misc"))
    deleted_heartbeat = asyncio.run(presence_repository.delete(heartbeat.id))
    deleted_edge = asyncio.run(relay_repository.delete(edge.id))

    assert saved_heartbeat.presence == "busy"
    assert saved_edge.hop_number == 2
    assert len(listed_heartbeats) == 1
    assert deleted_heartbeat is True
    assert deleted_edge is True
    assert asyncio.run(presence_repository.get(heartbeat.id)) is None
    assert asyncio.run(relay_repository.get(edge.id)) is None
    assert asyncio.run(session_repository.delete("ses_misc")) is True
    assert asyncio.run(agent_repository.delete("agt_misc")) is True
