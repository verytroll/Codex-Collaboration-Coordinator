from __future__ import annotations

import asyncio

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


def _participant(*, agent_id: str, is_lead: int) -> SessionParticipantRecord:
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
    )


def test_non_lead_agent_can_target_self_but_not_others() -> None:
    service = CommandPermissions(_ParticipantRepository(_participant(agent_id="agt_1", is_lead=0)))
    sender = asyncio.run(
        service.resolve_sender(
            session_id="ses_001",
            sender_type="agent",
            sender_id="agt_1",
        )
    )

    service.require_target_permission(
        command_name="interrupt",
        sender=sender,
        target_agent_id="agt_1",
    )

    with pytest.raises(CommandPermissionError):
        service.require_target_permission(
            command_name="interrupt",
            sender=sender,
            target_agent_id="agt_2",
        )


def test_user_sender_bypasses_agent_permission_checks() -> None:
    service = CommandPermissions(_ParticipantRepository(None))
    sender = asyncio.run(
        service.resolve_sender(
            session_id="ses_001",
            sender_type="user",
            sender_id="usr_001",
        )
    )

    assert sender.participant is None
    assert sender.is_lead is True

    service.require_target_permission(
        command_name="new",
        sender=sender,
        target_agent_id="agt_1",
    )
