"""Local demo data seeding helpers."""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from typing import Sequence

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.channels import SessionChannelRepository
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.phases import PhaseRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.channel_service import ChannelService
from app.services.phase_service import PhaseService
from app.services.relay_templates import RelayTemplatesService

DEFAULT_DEMO_SESSION_ID = "ses_demo"
DEFAULT_DEMO_AGENTS: tuple[tuple[str, str, str, bool], ...] = (
    ("agt_planner_demo", "Planner", "planner", True),
    ("agt_builder_demo", "Builder", "builder", False),
    ("agt_reviewer_demo", "Reviewer", "reviewer", False),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _ensure_agent_and_runtime(
    *,
    database_url: str,
    agent_id: str,
    display_name: str,
    role: str,
    is_lead: bool,
    now: str,
) -> str:
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    agent = await agent_repository.get(agent_id)
    if agent is None:
        agents = await agent_repository.list()
        agent = next((item for item in agents if item.display_name == display_name), None)
    if agent is None:
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
        actual_agent_id = agent_id
    else:
        actual_agent_id = agent.id
        if (
            agent.display_name != display_name
            or agent.role != role
            or agent.is_lead_default != int(is_lead)
            or agent.runtime_kind != "codex"
            or agent.status != "active"
        ):
            await agent_repository.update(
                AgentRecord(
                    id=agent.id,
                    display_name=display_name,
                    role=role,
                    is_lead_default=int(is_lead),
                    runtime_kind="codex",
                    capabilities_json=agent.capabilities_json,
                    default_config_json=agent.default_config_json,
                    status="active",
                    created_at=agent.created_at,
                    updated_at=now,
                )
            )
    runtime_id = f"rt_demo_{actual_agent_id}"
    if await runtime_repository.get(runtime_id) is None:
        await runtime_repository.create(
            AgentRuntimeRecord(
                id=runtime_id,
                agent_id=actual_agent_id,
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
    return actual_agent_id


async def _ensure_demo_session(
    *,
    database_url: str,
    now: str,
    lead_agent_id: str,
) -> None:
    session_repository = SessionRepository(database_url)
    session = await session_repository.get(DEFAULT_DEMO_SESSION_ID)
    if session is None:
        await session_repository.create(
            SessionRecord(
                id=DEFAULT_DEMO_SESSION_ID,
                title="Demo session",
                goal="Show the local coordinator MVP",
                status="active",
                lead_agent_id=lead_agent_id,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        return

    if session.lead_agent_id != lead_agent_id or session.status != "active":
        await session_repository.update(
            SessionRecord(
                id=session.id,
                title="Demo session",
                goal="Show the local coordinator MVP",
                status="active",
                lead_agent_id=lead_agent_id,
                active_phase_id=session.active_phase_id,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=session.last_message_at,
                template_key=session.template_key,
                created_at=session.created_at,
                updated_at=now,
            )
        )


async def _ensure_demo_participant(
    *,
    database_url: str,
    agent_id: str,
    role: str,
    is_lead: bool,
    now: str,
) -> None:
    participant_repository = ParticipantRepository(database_url)
    participant_id = f"sp_{DEFAULT_DEMO_SESSION_ID}_{agent_id}"
    if await participant_repository.get(participant_id) is None:
        await participant_repository.create(
            SessionParticipantRecord(
                id=participant_id,
                session_id=DEFAULT_DEMO_SESSION_ID,
                agent_id=agent_id,
                runtime_id=None,
                is_lead=1 if is_lead else 0,
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


async def seed_demo_data(database_url: str) -> None:
    """Seed demo data used by smoke and release checks."""
    await migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)

    now = _utc_now()
    resolved_agent_ids: dict[str, str] = {}
    for agent_id, display_name, role, is_lead in DEFAULT_DEMO_AGENTS:
        resolved_agent_ids[agent_id] = await _ensure_agent_and_runtime(
            database_url=database_url,
            agent_id=agent_id,
            display_name=display_name,
            role=role,
            is_lead=is_lead,
            now=now,
        )

    await _ensure_demo_session(
        database_url=database_url,
        now=now,
        lead_agent_id=resolved_agent_ids["agt_planner_demo"],
    )

    for agent_id, _, role, is_lead in DEFAULT_DEMO_AGENTS:
        await _ensure_demo_participant(
            database_url=database_url,
            agent_id=resolved_agent_ids[agent_id],
            role=role,
            is_lead=is_lead,
            now=now,
        )

    channel_repository = SessionChannelRepository(database_url)
    phase_repository = PhaseRepository(database_url)
    channel_service = ChannelService(channel_repository)
    phase_service = PhaseService(
        phase_repository=phase_repository,
        session_repository=SessionRepository(database_url),
        relay_templates_service=RelayTemplatesService(),
    )
    await channel_service.ensure_default_channels(DEFAULT_DEMO_SESSION_ID)
    await phase_service.ensure_default_phases(DEFAULT_DEMO_SESSION_ID)
    await phase_service.activate_phase_by_key(DEFAULT_DEMO_SESSION_ID, "planning")

    print(
        "Seeded demo data: ses_demo, agt_planner_demo, agt_builder_demo, "
        "agt_reviewer_demo, default channels, and planning phase"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Seed demo data from the command line."""
    parser = argparse.ArgumentParser(description="Seed local demo data.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./codex_coordinator.db"),
        help="SQLite database URL to seed",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    asyncio.run(seed_demo_data(args.database_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
