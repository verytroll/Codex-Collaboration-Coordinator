"""Command handlers for text commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import MessageRecord
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.job_service import JobService
from app.services.mention_router import MentionRouter, ResolvedMention
from app.services.message_parser import MessageParser, ParsedCommand, ParsedMessage
from app.services.offline_queue import OfflineQueueService
from app.services.review_mode import ReviewModeService
from app.services.permissions import CommandPermissions
from app.services.relay_engine import RelayEngine


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class CommandExecutionResult:
    """Result from a command handler."""

    command_name: str
    target_agent_id: str
    target_job_id: str | None
    relay_result: str | None


class CommandHandler:
    """Parse and execute text commands."""

    def __init__(
        self,
        *,
        job_service: JobService,
        job_repository: JobRepository,
        participant_repository: ParticipantRepository,
        agent_repository: AgentRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository,
        permissions: CommandPermissions,
        relay_engine: RelayEngine,
        offline_queue_service: OfflineQueueService,
        review_mode_service: ReviewModeService,
        parser: MessageParser | None = None,
    ) -> None:
        self.job_service = job_service
        self.job_repository = job_repository
        self.participant_repository = participant_repository
        self.agent_repository = agent_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.permissions = permissions
        self.relay_engine = relay_engine
        self.offline_queue_service = offline_queue_service
        self.review_mode_service = review_mode_service
        self.parser = parser or MessageParser()
        self.mention_router = MentionRouter()

    async def handle_command(
        self,
        *,
        session_id: str,
        sender_type: str,
        sender_id: str | None,
        message: MessageRecord,
        command: ParsedCommand,
    ) -> CommandExecutionResult:
        """Execute a command parsed from a message."""
        target_agent_id = await self._resolve_target_agent_id(
            session_id=session_id,
            sender_type=sender_type,
            sender_id=sender_id,
            command=command,
        )
        sender = await self.permissions.resolve_sender(
            session_id=session_id,
            sender_type=sender_type,
            sender_id=sender_id,
        )
        self.permissions.require_target_permission(
            command_name=command.command_name,
            sender=sender,
            target_agent_id=target_agent_id,
        )

        if command.command_name == "new":
            job = await self.job_service.create_job_for_agent(
                session_id=session_id,
                channel_key=message.channel_key,
                agent_id=target_agent_id,
                title=self._build_title(command),
                instructions=command.arguments or message.content,
                source_message_id=message.id,
            )
            await self._record_command_event(
                session_id=session_id,
                sender_type=sender_type,
                sender_id=sender_id,
                command_name="new",
                target_agent_id=target_agent_id,
                target_job_id=job.id,
            )
            dispatch_result = await self.offline_queue_service.schedule_job(
                job.id,
                input_type="command.new",
                input_payload={
                    "command_name": "new",
                    "arguments": command.arguments,
                    "source_message_id": message.id,
                },
                relay_reason="manual_relay",
            )
            return CommandExecutionResult(
                command_name="new",
                target_agent_id=target_agent_id,
                target_job_id=job.id,
                relay_result=(
                    dispatch_result.relay_result.event_type
                    if dispatch_result.relay_result is not None
                    else "job.queued_offline"
                ),
            )

        target_job = await self._resolve_target_job(session_id, target_agent_id)
        if target_job is None:
            raise LookupError(
                f"No active job found for agent {target_agent_id} in session {session_id}"
            )

        if command.command_name == "review":
            review_result = await self.review_mode_service.request_review(
                source_job_id=target_job.id,
                requested_by_agent_id=sender_id if sender_type == "agent" else None,
                notes=command.arguments or None,
            )
            await self._record_command_event(
                session_id=session_id,
                sender_type=sender_type,
                sender_id=sender_id,
                command_name="review",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
            )
            return CommandExecutionResult(
                command_name="review",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
                relay_result="review.requested",
            )

        if command.command_name == "interrupt":
            relay_result = await self.relay_engine.interrupt_job(
                target_job.id,
                reason=command.arguments or None,
            )
            await self._record_command_event(
                session_id=session_id,
                sender_type=sender_type,
                sender_id=sender_id,
                command_name="interrupt",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
            )
            return CommandExecutionResult(
                command_name="interrupt",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
                relay_result=relay_result.event_type,
            )

        if command.command_name == "compact":
            relay_result = await self.relay_engine.compact_job(
                target_job.id,
                reason=command.arguments or None,
            )
            await self._record_command_event(
                session_id=session_id,
                sender_type=sender_type,
                sender_id=sender_id,
                command_name="compact",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
            )
            return CommandExecutionResult(
                command_name="compact",
                target_agent_id=target_agent_id,
                target_job_id=target_job.id,
                relay_result=relay_result.event_type,
            )

        raise LookupError(f"Unsupported command: {command.command_name}")

    async def _resolve_target_agent_id(
        self,
        *,
        session_id: str,
        sender_type: str,
        sender_id: str | None,
        command: ParsedCommand,
    ) -> str:
        parsed: ParsedMessage = self.parser.parse(command.arguments)
        if parsed.mentions:
            participants = await self.participant_repository.list_by_session(session_id)
            agents = await self.agent_repository.list()
            resolved = self._resolve_mentions(parsed, participants, agents)
            if resolved:
                return resolved[0].mentioned_agent_id

        if sender_type == "agent" and sender_id is not None:
            return sender_id

        raise LookupError(f"Command /{command.command_name} requires a target agent")

    def _resolve_mentions(
        self,
        parsed: ParsedMessage,
        participants: list[SessionParticipantRecord],
        agents: list[AgentRecord],
    ) -> list[ResolvedMention]:
        return self.mention_router.resolve_mentions(
            parsed.mentions,
            participants,
            agents,
        )

    async def _resolve_target_job(
        self,
        session_id: str,
        agent_id: str,
    ) -> JobRecord | None:
        jobs = await self.job_repository.list_by_session(session_id)
        terminal_statuses = {
            "completed",
            "interrupted",
            "canceled",
            "failed",
            "paused_by_loop_guard",
        }
        candidate_jobs = [
            job
            for job in jobs
            if job.assigned_agent_id == agent_id and job.status not in terminal_statuses
        ]
        if candidate_jobs:
            return max(candidate_jobs, key=lambda job: (job.created_at, job.id))
        matching = [job for job in jobs if job.assigned_agent_id == agent_id]
        if not matching:
            return None
        return max(matching, key=lambda job: (job.created_at, job.id))

    async def _record_command_event(
        self,
        *,
        session_id: str,
        sender_type: str,
        sender_id: str | None,
        command_name: str,
        target_agent_id: str,
        target_job_id: str | None,
    ) -> None:
        from app.services.session_events import record_session_event

        await record_session_event(
            self.session_event_repository,
            session_id=session_id,
            event_type=f"command.{command_name}",
            actor_type=sender_type,
            actor_id=sender_id,
            payload={
                "command_name": command_name,
                "target_agent_id": target_agent_id,
                "target_job_id": target_job_id,
            },
            created_at=_utc_now(),
        )

    @staticmethod
    def _build_title(command: ParsedCommand) -> str:
        """Build a title for a `/new` job."""
        text = command.arguments.strip()
        return text[:120] if text else "New work item"
