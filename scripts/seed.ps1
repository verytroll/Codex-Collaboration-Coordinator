$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    $env:DATABASE_URL = "sqlite:///./codex_coordinator.db"
}

@'
import asyncio
import os
from datetime import datetime, timezone

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord, AgentRepository, AgentRuntimeRecord, AgentRuntimeRepository
from app.repositories.channels import SessionChannelRepository
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.phases import PhaseRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.channel_service import ChannelService
from app.services.phase_service import PhaseService
from app.services.relay_templates import RelayTemplatesService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _seed() -> None:
    database_url = os.environ["DATABASE_URL"]
    await migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)

    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    session_repository = SessionRepository(database_url)
    participant_repository = ParticipantRepository(database_url)
    channel_repository = SessionChannelRepository(database_url)
    phase_repository = PhaseRepository(database_url)
    channel_service = ChannelService(channel_repository)
    phase_service = PhaseService(
        phase_repository=phase_repository,
        session_repository=session_repository,
        relay_templates_service=RelayTemplatesService(),
    )

    now = _utc_now()
    specs = [
        ("agt_planner_demo", "Planner", "planner", True),
        ("agt_builder_demo", "Builder", "builder", False),
        ("agt_reviewer_demo", "Reviewer", "reviewer", False),
    ]
    for agent_id, display_name, role, is_lead in specs:
        if await agent_repository.get(agent_id) is None:
            await agent_repository.create(
                AgentRecord(
                    id=agent_id,
                    display_name=display_name,
                    role=role,
                    is_lead_default=int(is_lead),
                    runtime_kind="codex",
                    capabilities_json=None,
                    default_config_json=None,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
        runtime_id = f"rt_demo_{agent_id}"
        if await runtime_repository.get(runtime_id) is None:
            await runtime_repository.create(
                AgentRuntimeRecord(
                    id=runtime_id,
                    agent_id=agent_id,
                    runtime_kind="codex",
                    transport_kind="stdio",
                    transport_config_json=None,
                    workspace_path="/workspace/project",
                    approval_policy=None,
                    sandbox_policy="workspace-write",
                    runtime_status="offline",
                    last_heartbeat_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )

    if await session_repository.get("ses_demo") is None:
        await session_repository.create(
            SessionRecord(
                id="ses_demo",
                title="Demo session",
                goal="Show the local coordinator MVP",
                status="active",
                lead_agent_id="agt_planner_demo",
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at=now,
                updated_at=now,
            )
        )

    participants = [
        ("agt_planner_demo", 1, "planner"),
        ("agt_builder_demo", 0, "builder"),
        ("agt_reviewer_demo", 0, "reviewer"),
    ]
    for agent_id, is_lead, role in participants:
        participant_id = f"sp_ses_demo_{agent_id}"
        if await participant_repository.get(participant_id) is None:
            await participant_repository.create(
                SessionParticipantRecord(
                    id=participant_id,
                    session_id="ses_demo",
                    agent_id=agent_id,
                    runtime_id=None,
                    is_lead=is_lead,
                    read_scope="shared_history",
                    write_scope="mention_or_direct_assignment",
                    participant_status="joined",
                    joined_at=now,
                    left_at=None,
                    created_at=now,
                    updated_at=now,
                    role=role,
                )
            )
    await channel_service.ensure_default_channels("ses_demo")
    await phase_service.ensure_default_phases("ses_demo")
    await phase_service.activate_phase_by_key("ses_demo", "planning")

    print(
        "Seeded demo data: ses_demo, agt_planner_demo, agt_builder_demo, "
        "agt_reviewer_demo, default channels, and planning phase"
    )


asyncio.run(_seed())
'@ | python -
