"""Permission helpers for command execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.participants import ParticipantRepository, SessionParticipantRecord


class CommandPermissionError(PermissionError):
    """Raised when a command sender is not allowed to act."""


@dataclass(frozen=True, slots=True)
class CommandPermissionCheck:
    """Resolved command sender context."""

    participant: SessionParticipantRecord | None
    is_lead: bool


class CommandPermissions:
    """Evaluate command permissions against session participants."""

    def __init__(self, participant_repository: ParticipantRepository) -> None:
        self.participant_repository = participant_repository

    async def resolve_sender(
        self,
        *,
        session_id: str,
        sender_type: str,
        sender_id: str | None,
    ) -> CommandPermissionCheck:
        """Resolve the sender participant and lead status."""
        if sender_type != "agent":
            return CommandPermissionCheck(participant=None, is_lead=True)
        if sender_id is None:
            raise CommandPermissionError("sender_id is required for agent commands")

        participant = await self.participant_repository.get_by_session_and_agent(
            session_id,
            sender_id,
        )
        if participant is None:
            raise CommandPermissionError(
                f"Agent {sender_id} is not a participant of session {session_id}"
            )
        return CommandPermissionCheck(participant=participant, is_lead=participant.is_lead == 1)

    def require_target_permission(
        self,
        *,
        command_name: str,
        sender: CommandPermissionCheck,
        target_agent_id: str,
    ) -> None:
        """Enforce basic lead/self-target command permissions."""
        if sender.participant is None:
            return
        if sender.is_lead or sender.participant.agent_id == target_agent_id:
            return
        raise CommandPermissionError(
            f"Agent {sender.participant.agent_id} cannot run /{command_name} on {target_agent_id}"
        )
