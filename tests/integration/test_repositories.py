from __future__ import annotations

import asyncio
from dataclasses import replace

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.channels import SessionChannelRecord, SessionChannelRepository
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'repositories.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def test_session_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository = SessionRepository(database_url)
    agent_repository = AgentRepository(database_url)

    lead_agent = AgentRecord(
        id="agt_lead",
        display_name="Lead Agent",
        role="builder",
        is_lead_default=1,
        runtime_kind="codex",
        capabilities_json=None,
        default_config_json=None,
        status="active",
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    session = SessionRecord(
        id="ses_001",
        title="Initial session",
        goal="Bootstrap repository layer",
        status="draft",
        lead_agent_id=lead_agent.id,
        active_phase_id=None,
        loop_guard_status="normal",
        loop_guard_reason=None,
        last_message_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    created_agent = asyncio.run(agent_repository.create(lead_agent))
    created_session = asyncio.run(session_repository.create(session))
    fetched_session = asyncio.run(session_repository.get(session.id))
    updated_session = replace(created_session, title="Updated session", status="active")

    assert created_agent == lead_agent
    assert created_session == session
    assert fetched_session == session

    saved_session = asyncio.run(session_repository.update(updated_session))
    listed_sessions = asyncio.run(session_repository.list())
    deleted = asyncio.run(session_repository.delete(session.id))

    assert saved_session.title == "Updated session"
    assert len(listed_sessions) == 1
    assert deleted is True
    assert asyncio.run(session_repository.get(session.id)) is None
    assert asyncio.run(agent_repository.delete(lead_agent.id)) is True


def test_session_channel_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    session_repository = SessionRepository(database_url)
    channel_repository = SessionChannelRepository(database_url)

    session = SessionRecord(
        id="ses_channel",
        title="Channel session",
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
    channel = SessionChannelRecord(
        id="chn_001",
        session_id=session.id,
        channel_key="planning",
        display_name="Planning",
        description="Planning channel",
        is_default=False,
        sort_order=20,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    asyncio.run(session_repository.create(session))
    created_channel = asyncio.run(channel_repository.create(channel))
    fetched_channel = asyncio.run(channel_repository.get(channel.id))
    fetched_by_key = asyncio.run(channel_repository.get_by_session_and_key(session.id, "planning"))
    updated_channel = replace(created_channel, display_name="Planning v2")

    assert created_channel == channel
    assert fetched_channel == channel
    assert fetched_by_key == channel

    saved_channel = asyncio.run(channel_repository.update(updated_channel))
    listed_channels = asyncio.run(channel_repository.list_by_session(session.id))
    deleted = asyncio.run(channel_repository.delete(channel.id))

    assert saved_channel.display_name == "Planning v2"
    assert len(listed_channels) == 1
    assert deleted is True
    assert asyncio.run(channel_repository.get(channel.id)) is None
    assert asyncio.run(session_repository.delete(session.id)) is True


def test_agent_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    agent_repository = AgentRepository(database_url)

    agent = AgentRecord(
        id="agt_001",
        display_name="Builder",
        role="builder",
        is_lead_default=0,
        runtime_kind="codex",
        capabilities_json='["code"]',
        default_config_json='{"model":"gpt-5"}',
        status="active",
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    created_agent = asyncio.run(agent_repository.create(agent))
    fetched_agent = asyncio.run(agent_repository.get(agent.id))
    updated_agent = replace(created_agent, display_name="Builder Pro", status="disabled")

    assert created_agent == agent
    assert fetched_agent == agent

    saved_agent = asyncio.run(agent_repository.update(updated_agent))
    listed_agents = asyncio.run(agent_repository.list())
    deleted = asyncio.run(agent_repository.delete(agent.id))

    assert saved_agent.display_name == "Builder Pro"
    assert len(listed_agents) == 1
    assert deleted is True
    assert asyncio.run(agent_repository.get(agent.id)) is None


def test_agent_runtime_repository_crud(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)

    agent = AgentRecord(
        id="agt_runtime",
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
    runtime = AgentRuntimeRecord(
        id="rt_001",
        agent_id=agent.id,
        runtime_kind="codex_app_server",
        transport_kind="stdio",
        transport_config_json='{"command":"codex"}',
        workspace_path="C:/workspace",
        approval_policy="default",
        sandbox_policy="default",
        runtime_status="starting",
        last_heartbeat_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    asyncio.run(agent_repository.create(agent))
    created_runtime = asyncio.run(runtime_repository.create(runtime))
    fetched_runtime = asyncio.run(runtime_repository.get(runtime.id))
    updated_runtime = replace(created_runtime, runtime_status="online")

    assert created_runtime == runtime
    assert fetched_runtime == runtime

    saved_runtime = asyncio.run(runtime_repository.update(updated_runtime))
    listed_runtimes = asyncio.run(runtime_repository.list())
    deleted = asyncio.run(runtime_repository.delete(runtime.id))

    assert saved_runtime.runtime_status == "online"
    assert len(listed_runtimes) == 1
    assert deleted is True
    assert asyncio.run(runtime_repository.get(runtime.id)) is None
    assert asyncio.run(agent_repository.delete(agent.id)) is True


def test_participant_repository_crud_and_lookup(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    session_repository = SessionRepository(database_url)
    participant_repository = ParticipantRepository(database_url)

    agent = AgentRecord(
        id="agt_participant",
        display_name="Participant",
        role="reviewer",
        is_lead_default=0,
        runtime_kind="codex",
        capabilities_json=None,
        default_config_json=None,
        status="active",
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    runtime = AgentRuntimeRecord(
        id="rt_participant",
        agent_id=agent.id,
        runtime_kind="codex_app_server",
        transport_kind="stdio",
        transport_config_json=None,
        workspace_path=None,
        approval_policy=None,
        sandbox_policy=None,
        runtime_status="online",
        last_heartbeat_at="2026-03-31T00:00:00Z",
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )
    session = SessionRecord(
        id="ses_participant",
        title="Participant session",
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
    participant = SessionParticipantRecord(
        id="sp_001",
        session_id=session.id,
        agent_id=agent.id,
        runtime_id=runtime.id,
        is_lead=1,
        read_scope="shared_history",
        write_scope="full",
        participant_status="joined",
        joined_at="2026-03-31T00:00:00Z",
        left_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    asyncio.run(agent_repository.create(agent))
    asyncio.run(runtime_repository.create(runtime))
    asyncio.run(session_repository.create(session))

    created_participant = asyncio.run(participant_repository.create(participant))
    fetched_by_id = asyncio.run(participant_repository.get(participant.id))
    fetched_by_pair = asyncio.run(
        participant_repository.get_by_session_and_agent(session.id, agent.id)
    )
    updated_participant = replace(
        created_participant,
        participant_status="left",
        left_at="2026-03-31T01:00:00Z",
    )

    assert created_participant == participant
    assert fetched_by_id == participant
    assert fetched_by_pair == participant

    saved_participant = asyncio.run(participant_repository.update(updated_participant))
    listed_participants = asyncio.run(participant_repository.list_by_session(session.id))
    deleted = asyncio.run(participant_repository.delete(participant.id))

    assert saved_participant.participant_status == "left"
    assert len(listed_participants) == 1
    assert deleted is True
    assert asyncio.run(participant_repository.get(participant.id)) is None
    assert asyncio.run(runtime_repository.delete(runtime.id)) is True
    assert asyncio.run(session_repository.delete(session.id)) is True
    assert asyncio.run(agent_repository.delete(agent.id)) is True
