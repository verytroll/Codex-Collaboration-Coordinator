from __future__ import annotations

import pytest

from app.repositories.agents import AgentRecord
from app.repositories.participants import SessionParticipantRecord
from app.services.mention_router import MentionRouter
from app.services.message_parser import ParsedMention


def test_mention_router_resolves_active_participant_by_display_name() -> None:
    router = MentionRouter()
    participants = [
        SessionParticipantRecord(
            id="sp_001",
            session_id="ses_001",
            agent_id="agt_builder",
            runtime_id="rt_builder",
            is_lead=0,
            read_scope="shared_history",
            write_scope="mention_or_direct_assignment",
            participant_status="joined",
            joined_at="2026-03-31T00:00:00Z",
            left_at=None,
            created_at="2026-03-31T00:00:00Z",
            updated_at="2026-03-31T00:00:00Z",
        )
    ]
    agents = [
        AgentRecord(
            id="agt_builder",
            display_name="Builder",
            role="builder",
            is_lead_default=0,
            runtime_kind="codex",
            capabilities_json=None,
            default_config_json=None,
            status="active",
            created_at="2026-03-31T00:00:00Z",
            updated_at="2026-03-31T00:00:00Z",
        )
    ]

    resolved = router.resolve_mentions(
        [ParsedMention("#builder", "builder", 0, 0, 8)],
        participants,
        agents,
    )

    assert len(resolved) == 1
    assert resolved[0].mentioned_agent_id == "agt_builder"
    assert resolved[0].participant_id == "sp_001"
    assert resolved[0].runtime_id == "rt_builder"


def test_mention_router_rejects_unknown_mentions() -> None:
    router = MentionRouter()

    with pytest.raises(LookupError):
        router.resolve_mentions(
            [ParsedMention("#unknown", "unknown", 0, 0, 8)],
            [],
            [],
        )
