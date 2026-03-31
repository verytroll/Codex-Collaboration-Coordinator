from __future__ import annotations

import asyncio
import json

import pytest

from app.repositories.participants import SessionParticipantRecord
from app.services.permissions import CommandPermissionError, CommandPermissions


class _ParticipantRepository:
    def __init__(self, participant: SessionParticipantRecord | None) -> None:
        self.participant = participant

    async def get_by_session_and_agent(
        self,
        session_id: str,
        agent_id: str,
    ) -> SessionParticipantRecord | None:
        if self.participant is None:
            return None
        if self.participant.session_id == session_id and self.participant.agent_id == agent_id:
            return self.participant
        return None


def _participant(
    *,
    agent_id: str,
    role: str,
    is_lead: int = 0,
    policy_json: str | None = None,
) -> SessionParticipantRecord:
    return SessionParticipantRecord(
        id=f"sp_{agent_id}",
        session_id="ses_001",
        agent_id=agent_id,
        runtime_id=None,
        is_lead=is_lead,
        read_scope="shared_history",
        write_scope="mention_or_direct_assignment",
        participant_status="joined",
        joined_at="2026-03-31T00:00:00Z",
        left_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
        role=role,
        policy_json=policy_json,
    )


def test_planner_can_target_other_agents() -> None:
    participant = _participant(agent_id="agt_planner", role="planner")
    service = CommandPermissions(_ParticipantRepository(participant))
    sender = asyncio.run(
        service.resolve_sender(
            session_id="ses_001",
            sender_type="agent",
            sender_id="agt_planner",
        )
    )

    assert sender.role == "planner"
    assert sender.policy is not None
    assert sender.policy.can_target_other_agents is True

    service.require_target_permission(
        command_name="new",
        sender=sender,
        target_agent_id="agt_builder",
    )
    service.require_target_permission(
        command_name="interrupt",
        sender=sender,
        target_agent_id="agt_builder",
    )


def test_reviewer_defaults_to_review_only_policy() -> None:
    participant = _participant(agent_id="agt_reviewer", role="reviewer")
    service = CommandPermissions(_ParticipantRepository(participant))
    sender = asyncio.run(
        service.resolve_sender(
            session_id="ses_001",
            sender_type="agent",
            sender_id="agt_reviewer",
        )
    )

    assert sender.role == "reviewer"
    assert sender.policy is not None
    assert sender.policy.review_only_actions is True
    assert sender.policy.can_relay is False
    assert sender.policy.can_create_job is False

    with pytest.raises(CommandPermissionError):
        service.require_target_permission(
            command_name="new",
            sender=sender,
            target_agent_id="agt_reviewer",
        )

    with pytest.raises(CommandPermissionError):
        service.require_target_permission(
            command_name="interrupt",
            sender=sender,
            target_agent_id="agt_builder",
        )


def test_custom_policy_override_allows_relay_without_job_creation() -> None:
    participant = _participant(
        agent_id="agt_reviewer",
        role="reviewer",
        policy_json=json.dumps(
            {
                "can_relay": True,
                "can_target_other_agents": True,
            },
            sort_keys=True,
        ),
    )
    service = CommandPermissions(_ParticipantRepository(participant))
    sender = asyncio.run(
        service.resolve_sender(
            session_id="ses_001",
            sender_type="agent",
            sender_id="agt_reviewer",
        )
    )

    assert sender.policy is not None
    assert sender.policy.can_relay is True
    assert sender.policy.can_target_other_agents is True
    assert sender.policy.can_create_job is False

    with pytest.raises(CommandPermissionError):
        service.require_target_permission(
            command_name="new",
            sender=sender,
            target_agent_id="agt_builder",
        )
