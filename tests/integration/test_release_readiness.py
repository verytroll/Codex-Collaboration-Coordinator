from __future__ import annotations

import asyncio
from pathlib import Path

from app.services.release_readiness import verify_release_readiness


def _database_url(tmp_path: Path, name: str) -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def test_release_readiness_checks_migrations_and_seed_reset(tmp_path) -> None:
    database_url = _database_url(tmp_path, "release_ready.db")

    result = asyncio.run(verify_release_readiness(database_url))

    assert result["migrations"] == (
        "001_baseline_tables.sql",
        "002_baseline_indexes.sql",
        "003_messages.sql",
        "004_jobs.sql",
        "005_presence_relay_session.sql",
        "006_session_channels.sql",
        "007_session_participant_policy.sql",
        "008_job_inputs.sql",
        "009_rules.sql",
        "010_transcript_exports.sql",
        "011_review_mode.sql",
        "012_phases.sql",
        "013_a2a_tasks.sql",
        "014_public_subscriptions.sql",
        "015_session_templates.sql",
        "016_orchestration_runs.sql",
        "017_runtime_pools.sql",
        "018_policy_conditions.sql",
    )

    snapshot = result["seed_snapshot"]
    assert snapshot.agent_ids == ("agt_builder_demo", "agt_planner_demo", "agt_reviewer_demo")
    assert snapshot.runtime_ids == (
        "rt_demo_agt_builder_demo",
        "rt_demo_agt_planner_demo",
        "rt_demo_agt_reviewer_demo",
    )
    assert snapshot.session_ids == ("ses_demo",)
    assert snapshot.participant_ids == (
        "sp_ses_demo_agt_builder_demo",
        "sp_ses_demo_agt_planner_demo",
        "sp_ses_demo_agt_reviewer_demo",
    )
    assert snapshot.channel_keys == ("debug", "general", "planning", "review")
    assert snapshot.phase_keys == ("finalize", "implementation", "planning", "review", "revise")
    assert snapshot.active_phase_key == "planning"
