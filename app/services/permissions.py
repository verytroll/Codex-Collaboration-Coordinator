"""Permission helpers for command execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.services.participant_policy import ParticipantPolicy, ParticipantPolicyService


class CommandPermissionError(PermissionError):
    """Raised when a command sender is not allowed to act."""


@dataclass(frozen=True, slots=True)
class CommandPermissionCheck:
    """Resolved command sender context."""

    participant: SessionParticipantRecord | None
    is_lead: bool
    role: str | None = None
    policy: ParticipantPolicy | None = None


class CommandPermissions:
    """Evaluate command permissions against session participants."""

    def __init__(
        self,
        participant_repository: ParticipantRepository,
        participant_policy_service: ParticipantPolicyService | None = None,
    ) -> None:
        self.participant_repository = participant_repository
        self.participant_policy_service = (
            participant_policy_service
            if participant_policy_service is not None
            else ParticipantPolicyService()
        )

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
        policy = self.participant_policy_service.resolve_policy(
            role=participant.role,
            policy_json=participant.policy_json,
            is_lead=participant.is_lead == 1,
        )
        return CommandPermissionCheck(
            participant=participant,
            is_lead=participant.is_lead == 1,
            role=participant.role,
            policy=policy,
        )

    def require_target_permission(
        self,
        *,
        command_name: str,
        sender: CommandPermissionCheck,
        target_agent_id: str,
    ) -> None:
        """Enforce lead and role-based command permissions."""
        if sender.participant is None:
            return
        if sender.is_lead:
            return
        policy = sender.policy or self.participant_policy_service.default_policy_for_role(
            sender.role or sender.participant.role,
            is_lead=sender.is_lead,
        )
        command_permissions = {
            "new": policy.can_create_job,
            "interrupt": policy.can_interrupt,
            "compact": policy.can_compact,
        }
        if command_name == "review":
            if policy.review_only_actions:
                if (
                    target_agent_id != sender.participant.agent_id
                    and not policy.can_target_other_agents
                ):
                    raise CommandPermissionError(
                        f"Agent {sender.participant.agent_id} cannot run /{command_name} "
                        f"on {target_agent_id}"
                    )
                return
            raise CommandPermissionError(
                f"Agent {sender.participant.agent_id} cannot run /{command_name} in this session"
            )
        if not command_permissions.get(command_name, False):
            raise CommandPermissionError(
                f"Agent {sender.participant.agent_id} cannot run /{command_name} in this session"
            )
        if target_agent_id != sender.participant.agent_id and not policy.can_target_other_agents:
            raise CommandPermissionError(
                f"Agent {sender.participant.agent_id} cannot run /{command_name} "
                f"on {target_agent_id}"
            )
        return
