"""Basic rules engine for session collaboration policy."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.repositories.jobs import JobRecord
from app.repositories.rules import RuleRecord, RuleRepository

RULE_TYPES = {
    "relay",
    "review_required",
    "approval_escalation",
    "channel_routing_preference",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True, slots=True)
class RuleEvaluationResult:
    """Resolved rule outcome for a job or routing decision."""

    dispatch_allowed: bool
    channel_key: str
    matched_rule_ids: list[str]
    hold_reason: str | None = None


class RuleEngineService:
    """Store and evaluate session rules."""

    def __init__(self, rule_repository: RuleRepository) -> None:
        self.rule_repository = rule_repository

    async def create_rule(
        self,
        *,
        session_id: str,
        rule_type: str,
        name: str,
        description: str | None = None,
        priority: int = 100,
        is_active: bool = False,
        conditions: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
    ) -> RuleRecord:
        if rule_type not in RULE_TYPES:
            raise ValueError(f"Unsupported rule type: {rule_type}")
        now = _utc_now()
        rule = RuleRecord(
            id=f"rul_{uuid4().hex}",
            session_id=session_id,
            rule_type=rule_type,
            name=name,
            description=description,
            is_active=1 if is_active else 0,
            priority=priority,
            conditions_json=json.dumps(conditions, sort_keys=True)
            if conditions is not None
            else None,
            actions_json=json.dumps(actions, sort_keys=True) if actions is not None else None,
            created_at=now,
            updated_at=now,
        )
        return await self.rule_repository.create(rule)

    async def list_rules(self, session_id: str) -> list[RuleRecord]:
        return await self.rule_repository.list_by_session(session_id)

    async def get_rule(self, rule_id: str) -> RuleRecord | None:
        return await self.rule_repository.get(rule_id)

    async def activate_rule(self, rule_id: str) -> RuleRecord:
        rule = await self._ensure_rule(rule_id)
        updated = replace(rule, is_active=1, updated_at=_utc_now())
        return await self.rule_repository.update(updated)

    async def deactivate_rule(self, rule_id: str) -> RuleRecord:
        rule = await self._ensure_rule(rule_id)
        updated = replace(rule, is_active=0, updated_at=_utc_now())
        return await self.rule_repository.update(updated)

    async def resolve_job_dispatch(
        self,
        job: JobRecord,
    ) -> RuleEvaluationResult:
        active_rules = await self.rule_repository.list_active_by_session(job.session_id)
        channel_key = job.channel_key
        matched_rule_ids: list[str] = []
        hold_reason: str | None = None
        dispatch_allowed = True

        for rule in active_rules:
            if not self._matches_rule(rule, job=job):
                continue
            matched_rule_ids.append(rule.id)

            if rule.rule_type in {"relay", "channel_routing_preference"}:
                overridden_channel = self._resolve_target_channel(rule)
                if overridden_channel is not None:
                    channel_key = overridden_channel

            if rule.rule_type in {"review_required", "approval_escalation"}:
                dispatch_allowed = False
                hold_reason = rule.rule_type
                break

        return RuleEvaluationResult(
            dispatch_allowed=dispatch_allowed,
            channel_key=channel_key,
            matched_rule_ids=matched_rule_ids,
            hold_reason=hold_reason,
        )

    async def resolve_routing_channel(
        self,
        *,
        session_id: str,
        channel_key: str,
        agent_id: str | None = None,
        content: str | None = None,
    ) -> str:
        """Resolve the best channel for mention-based routing."""
        active_rules = await self.rule_repository.list_active_by_session(session_id)
        resolved_channel = channel_key
        for rule in active_rules:
            if rule.rule_type not in {"relay", "channel_routing_preference"}:
                continue
            if not self._matches_rule(
                rule, channel_key=channel_key, agent_id=agent_id, content=content
            ):
                continue
            overridden_channel = self._resolve_target_channel(rule)
            if overridden_channel is not None:
                resolved_channel = overridden_channel
        return resolved_channel

    async def _ensure_rule(self, rule_id: str) -> RuleRecord:
        rule = await self.rule_repository.get(rule_id)
        if rule is None:
            raise LookupError(f"Rule not found: {rule_id}")
        return rule

    def _matches_rule(
        self,
        rule: RuleRecord,
        *,
        job: JobRecord | None = None,
        channel_key: str | None = None,
        agent_id: str | None = None,
        content: str | None = None,
    ) -> bool:
        conditions = _parse_json(rule.conditions_json)
        if job is not None:
            channel_key = channel_key or job.channel_key
            agent_id = agent_id or job.assigned_agent_id
            content = content or job.instructions or job.title

        expected_channel_key = conditions.get("channel_key")
        if isinstance(expected_channel_key, str) and channel_key != expected_channel_key:
            return False

        expected_agent_id = conditions.get("agent_id") or conditions.get("assigned_agent_id")
        if isinstance(expected_agent_id, str) and agent_id != expected_agent_id:
            return False

        expected_message_contains = conditions.get("message_contains")
        if isinstance(expected_message_contains, str):
            if content is None or expected_message_contains.lower() not in content.lower():
                return False

        return True

    def _resolve_target_channel(self, rule: RuleRecord) -> str | None:
        actions = _parse_json(rule.actions_json)
        for key in ("target_channel_key", "channel_key"):
            value = actions.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
