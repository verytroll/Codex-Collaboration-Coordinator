"""Release readiness checks for local release candidates."""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.channels import SessionChannelRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.phases import PhaseRepository
from app.repositories.sessions import SessionRepository
from app.services.demo_seed import DEFAULT_DEMO_SESSION_ID, seed_demo_data


@dataclass(frozen=True, slots=True)
class DemoSeedSnapshot:
    """Repeatable signature for the seeded demo database."""

    agent_ids: tuple[str, ...]
    runtime_ids: tuple[str, ...]
    session_ids: tuple[str, ...]
    participant_ids: tuple[str, ...]
    channel_keys: tuple[str, ...]
    phase_keys: tuple[str, ...]
    active_phase_key: str | None


def _expected_demo_snapshot() -> DemoSeedSnapshot:
    return DemoSeedSnapshot(
        agent_ids=("agt_builder_demo", "agt_planner_demo", "agt_reviewer_demo"),
        runtime_ids=(
            "rt_demo_agt_builder_demo",
            "rt_demo_agt_planner_demo",
            "rt_demo_agt_reviewer_demo",
        ),
        session_ids=(DEFAULT_DEMO_SESSION_ID,),
        participant_ids=(
            "sp_ses_demo_agt_builder_demo",
            "sp_ses_demo_agt_planner_demo",
            "sp_ses_demo_agt_reviewer_demo",
        ),
        channel_keys=("debug", "general", "planning", "review"),
        phase_keys=("finalize", "implementation", "planning", "review", "revise"),
        active_phase_key="planning",
    )


async def verify_migration_round_trip(
    database_url: str,
    *,
    migrations_dir: Path | None = None,
) -> tuple[str, ...]:
    """Apply migrations twice and require the second run to be empty."""
    migration_dir = migrations_dir or DEFAULT_MIGRATIONS_DIR
    first_run = await migrate_sqlite(database_url, migrations_dir=migration_dir)
    second_run = await migrate_sqlite(database_url, migrations_dir=migration_dir)
    if not first_run:
        raise RuntimeError("Migration verification did not apply any migrations.")
    if second_run:
        raise RuntimeError(f"Migration verification was not idempotent: {second_run}")
    return tuple(first_run)


async def collect_demo_seed_snapshot(database_url: str) -> DemoSeedSnapshot:
    """Collect a stable signature of the seeded demo database."""
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    session_repository = SessionRepository(database_url)
    participant_repository = ParticipantRepository(database_url)
    channel_repository = SessionChannelRepository(database_url)
    phase_repository = PhaseRepository(database_url)

    agents, runtimes, sessions = await asyncio.gather(
        agent_repository.list(),
        runtime_repository.list(),
        session_repository.list(),
    )
    participants = await participant_repository.list_by_session(DEFAULT_DEMO_SESSION_ID)
    channels = await channel_repository.list_by_session(DEFAULT_DEMO_SESSION_ID)
    phases = await phase_repository.list_by_session(DEFAULT_DEMO_SESSION_ID)
    session = await session_repository.get(DEFAULT_DEMO_SESSION_ID)
    phase_by_id = {phase.id: phase.phase_key for phase in phases}

    return DemoSeedSnapshot(
        agent_ids=tuple(sorted(agent.id for agent in agents)),
        runtime_ids=tuple(sorted(runtime.id for runtime in runtimes)),
        session_ids=tuple(sorted(session_record.id for session_record in sessions)),
        participant_ids=tuple(sorted(participant.id for participant in participants)),
        channel_keys=tuple(sorted(channel.channel_key for channel in channels)),
        phase_keys=tuple(sorted(phase.phase_key for phase in phases)),
        active_phase_key=phase_by_id.get(session.active_phase_id) if session else None,
    )


async def verify_seed_round_trip(database_url: str) -> DemoSeedSnapshot:
    """Seed demo data twice and require the snapshot to stay stable."""
    await seed_demo_data(database_url)
    first_snapshot = await collect_demo_seed_snapshot(database_url)
    await seed_demo_data(database_url)
    second_snapshot = await collect_demo_seed_snapshot(database_url)
    expected_snapshot = _expected_demo_snapshot()
    if first_snapshot != second_snapshot:
        raise RuntimeError("Seed verification changed state on the second run.")
    if second_snapshot != expected_snapshot:
        raise RuntimeError("Seed verification did not produce the expected demo snapshot.")
    return second_snapshot


async def verify_release_readiness(
    database_url: str,
    *,
    migrations_dir: Path | None = None,
) -> dict[str, object]:
    """Run the release readiness checks for migrations and demo seeding."""
    migrations = await verify_migration_round_trip(
        database_url,
        migrations_dir=migrations_dir,
    )
    seed_snapshot = await verify_seed_round_trip(database_url)
    return {
        "migrations": migrations,
        "seed_snapshot": seed_snapshot,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run release readiness checks from the command line."""
    parser = argparse.ArgumentParser(description="Verify release readiness checks.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./codex_coordinator.db"),
        help="SQLite database URL to verify",
    )
    parser.add_argument(
        "--migrations-dir",
        default=str(DEFAULT_MIGRATIONS_DIR),
        help="Directory containing SQL migrations",
    )
    parser.add_argument(
        "--check",
        choices=("all", "migrations", "seed"),
        default="all",
        help="Which readiness check to run",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    migrations_dir = Path(args.migrations_dir)

    async def _run() -> dict[str, object]:
        if args.check == "migrations":
            migrations = await verify_migration_round_trip(
                args.database_url,
                migrations_dir=migrations_dir,
            )
            return {"migrations": migrations}
        if args.check == "seed":
            seed_snapshot = await verify_seed_round_trip(args.database_url)
            return {"seed_snapshot": seed_snapshot}
        return await verify_release_readiness(
            args.database_url,
            migrations_dir=migrations_dir,
        )

    result = asyncio.run(_run())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
