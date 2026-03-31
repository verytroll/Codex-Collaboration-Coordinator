"""Mention routing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.repositories.agents import AgentRecord
from app.repositories.participants import SessionParticipantRecord
from app.services.message_parser import ParsedMention


def _normalize_token(value: str) -> str:
    """Normalize text for case-insensitive matching."""
    return "".join(character for character in value.lower() if character.isalnum())


@dataclass(frozen=True, slots=True)
class ResolvedMention:
    """A mention resolved to a participant and agent."""

    mention_text: str
    mention_name: str
    mention_order: int
    mentioned_agent_id: str
    participant_id: str
    runtime_id: str | None
    agent_display_name: str


class MentionRouter:
    """Resolve parsed mentions to active participants."""

    def resolve_mentions(
        self,
        mentions: list[ParsedMention],
        participants: list[SessionParticipantRecord],
        agents: list[AgentRecord],
    ) -> list[ResolvedMention]:
        """Resolve mention tokens against active participants."""
        active_participants = [
            participant
            for participant in participants
            if participant.participant_status == "joined" and participant.left_at is None
        ]
        agent_by_id = {agent.id: agent for agent in agents}
        resolved_mentions: list[ResolvedMention] = []
        for mention in mentions:
            resolved_mentions.append(
                self._resolve_single_mention(mention, active_participants, agent_by_id)
            )
        return resolved_mentions

    def _resolve_single_mention(
        self,
        mention: ParsedMention,
        participants: Iterable[SessionParticipantRecord],
        agents_by_id: dict[str, AgentRecord],
    ) -> ResolvedMention:
        """Resolve one mention to the best matching participant."""
        normalized_name = mention.normalized_name
        candidates: list[tuple[int, SessionParticipantRecord, AgentRecord]] = []
        for participant in participants:
            agent = agents_by_id.get(participant.agent_id)
            if agent is None:
                continue
            match_level = self._match_level(normalized_name, agent)
            if match_level is None:
                continue
            candidates.append((match_level, participant, agent))

        if not candidates:
            raise LookupError(f"No active participant matches mention {mention.mention_text}")

        candidates.sort(key=lambda item: (item[0], item[1].created_at, item[1].id))
        best_level = candidates[0][0]
        best_candidates = [candidate for candidate in candidates if candidate[0] == best_level]
        if len({candidate[2].id for candidate in best_candidates}) > 1:
            raise LookupError(f"Ambiguous mention {mention.mention_text}")

        _, participant, agent = best_candidates[0]
        return ResolvedMention(
            mention_text=mention.mention_text,
            mention_name=mention.mention_name,
            mention_order=mention.mention_order,
            mentioned_agent_id=agent.id,
            participant_id=participant.id,
            runtime_id=participant.runtime_id,
            agent_display_name=agent.display_name,
        )

    @staticmethod
    def _match_level(normalized_name: str, agent: AgentRecord) -> int | None:
        """Return how closely an agent matches a mention token."""
        if normalized_name == _normalize_token(agent.display_name):
            return 0
        if normalized_name == _normalize_token(agent.role):
            return 1
        if normalized_name == _normalize_token(agent.id):
            return 2
        return None
