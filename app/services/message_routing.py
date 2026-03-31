"""Message routing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.agents import AgentRepository
from app.repositories.messages import (
    MessageMentionRecord,
    MessageMentionRepository,
    MessageRecord,
)
from app.repositories.participants import ParticipantRepository
from app.services.job_service import JobService
from app.services.rule_engine import RuleEngineService
from app.services.mention_router import MentionRouter, ResolvedMention
from app.services.message_parser import MessageParser, ParsedCommand


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class MessageRoutingPlan:
    """Prepared routing plan for a message."""

    commands: list[ParsedCommand]
    resolved_mentions: list[ResolvedMention]


@dataclass(frozen=True, slots=True)
class MessageRoutingOutcome:
    """Result of applying routing to a stored message."""

    detected_mentions: list[str]
    created_jobs: list[str]


class MessageRoutingService:
    """Plan and apply message routing."""

    def __init__(
        self,
        *,
        message_mention_repository: MessageMentionRepository,
        participant_repository: ParticipantRepository,
        agent_repository: AgentRepository,
        job_service: JobService,
        rule_engine_service: RuleEngineService | None = None,
        parser: MessageParser | None = None,
        mention_router: MentionRouter | None = None,
    ) -> None:
        self.message_mention_repository = message_mention_repository
        self.participant_repository = participant_repository
        self.agent_repository = agent_repository
        self.job_service = job_service
        self.rule_engine_service = rule_engine_service
        self.parser = parser or MessageParser()
        self.mention_router = mention_router or MentionRouter()

    async def preview(self, *, session_id: str, content: str) -> MessageRoutingPlan:
        """Parse and resolve routing intent before persisting the message."""
        parsed_message = self.parser.parse(content)
        if parsed_message.has_command:
            return MessageRoutingPlan(commands=parsed_message.commands, resolved_mentions=[])

        participants = await self.participant_repository.list_by_session(session_id)
        agents = await self.agent_repository.list()
        resolved_mentions = self.mention_router.resolve_mentions(
            parsed_message.mentions,
            participants,
            agents,
        )
        return MessageRoutingPlan(
            commands=parsed_message.commands,
            resolved_mentions=resolved_mentions,
        )

    async def apply(
        self,
        *,
        message: MessageRecord,
        plan: MessageRoutingPlan,
    ) -> MessageRoutingOutcome:
        """Persist mention rows and jobs for a stored message."""
        if plan.commands:
            return MessageRoutingOutcome(detected_mentions=[], created_jobs=[])
        if not plan.resolved_mentions:
            return MessageRoutingOutcome(detected_mentions=[], created_jobs=[])

        created_at = _utc_now()
        effective_channel_key = message.channel_key
        if self.rule_engine_service is not None:
            effective_channel_key = await self.rule_engine_service.resolve_routing_channel(
                session_id=message.session_id,
                channel_key=message.channel_key,
                agent_id=message.sender_id,
                content=message.content,
            )
        for mention in plan.resolved_mentions:
            await self.message_mention_repository.create(
                MessageMentionRecord(
                    id=f"mmt_{uuid4().hex}",
                    message_id=message.id,
                    mentioned_agent_id=mention.mentioned_agent_id,
                    mention_text=mention.mention_text,
                    mention_order=mention.mention_order,
                    created_at=created_at,
                )
            )

        created_jobs = await self.job_service.create_jobs_for_mentions(
            message=message,
            mentions=plan.resolved_mentions,
            channel_key=effective_channel_key,
        )
        detected_mentions: list[str] = []
        seen_mentions: set[str] = set()
        for mention in plan.resolved_mentions:
            if mention.mentioned_agent_id in seen_mentions:
                continue
            detected_mentions.append(mention.mentioned_agent_id)
            seen_mentions.add(mention.mentioned_agent_id)
        return MessageRoutingOutcome(
            detected_mentions=detected_mentions,
            created_jobs=[job.id for job in created_jobs],
        )
