"""Participant role and policy helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Literal

ParticipantRole = Literal["planner", "builder", "reviewer", "researcher", "tester"]


@dataclass(frozen=True, slots=True)
class ParticipantPolicy:
    """Effective participant policy for a session."""

    can_relay: bool
    can_create_job: bool
    can_interrupt: bool
    can_compact: bool
    review_only_actions: bool
    can_target_other_agents: bool


class ParticipantPolicyService:
    """Resolve participant roles and effective permissions."""

    _ALLOWED_ROLES: frozenset[str] = frozenset(
        {"planner", "builder", "reviewer", "researcher", "tester"}
    )

    def default_role_for_agent(self, agent_role: str, *, is_lead: bool = False) -> ParticipantRole:
        """Return the default session role for an agent."""
        if is_lead:
            return "planner"
        normalized = agent_role.strip().lower()
        if normalized in self._ALLOWED_ROLES:
            return normalized  # type: ignore[return-value]
        return "builder"

    def default_policy_for_role(
        self,
        role: str,
        *,
        is_lead: bool = False,
    ) -> ParticipantPolicy:
        """Build the default policy matrix for a participant role."""
        if is_lead:
            return ParticipantPolicy(
                can_relay=True,
                can_create_job=True,
                can_interrupt=True,
                can_compact=True,
                review_only_actions=False,
                can_target_other_agents=True,
            )

        normalized = self._normalize_role(role)
        if normalized == "planner":
            return ParticipantPolicy(
                can_relay=True,
                can_create_job=True,
                can_interrupt=True,
                can_compact=True,
                review_only_actions=False,
                can_target_other_agents=True,
            )
        if normalized == "builder":
            return ParticipantPolicy(
                can_relay=True,
                can_create_job=True,
                can_interrupt=True,
                can_compact=True,
                review_only_actions=False,
                can_target_other_agents=False,
            )
        if normalized == "reviewer":
            return ParticipantPolicy(
                can_relay=False,
                can_create_job=False,
                can_interrupt=False,
                can_compact=False,
                review_only_actions=True,
                can_target_other_agents=False,
            )
        if normalized in {"researcher", "tester"}:
            return ParticipantPolicy(
                can_relay=True,
                can_create_job=False,
                can_interrupt=False,
                can_compact=False,
                review_only_actions=False,
                can_target_other_agents=False,
            )
        return ParticipantPolicy(
            can_relay=True,
            can_create_job=True,
            can_interrupt=True,
            can_compact=True,
            review_only_actions=False,
            can_target_other_agents=False,
        )

    def resolve_policy(
        self,
        *,
        role: str,
        policy_json: str | None,
        is_lead: bool = False,
    ) -> ParticipantPolicy:
        """Resolve the effective policy from stored JSON or defaults."""
        if policy_json is None:
            return self.default_policy_for_role(role, is_lead=is_lead)

        try:
            payload = json.loads(policy_json)
        except json.JSONDecodeError:
            return self.default_policy_for_role(role, is_lead=is_lead)

        if not isinstance(payload, dict):
            return self.default_policy_for_role(role, is_lead=is_lead)

        base = self.default_policy_for_role(role, is_lead=is_lead)
        overrides: dict[str, bool] = {}
        for field_name in asdict(base):
            value = payload.get(field_name)
            if isinstance(value, bool):
                overrides[field_name] = value
        if not overrides:
            return base
        return replace(base, **overrides)

    def policy_to_json(self, policy: ParticipantPolicy) -> str:
        """Serialize a policy to canonical JSON."""
        return json.dumps(asdict(policy), sort_keys=True)

    def policy_from_overrides(
        self,
        *,
        role: str,
        overrides: dict[str, bool | None],
        is_lead: bool = False,
    ) -> ParticipantPolicy:
        """Apply request overrides onto the default policy for a role."""
        base = self.default_policy_for_role(role, is_lead=is_lead)
        values = {
            field_name: value
            for field_name, value in overrides.items()
            if field_name in asdict(base) and isinstance(value, bool)
        }
        if not values:
            return base
        return replace(base, **values)

    def _normalize_role(self, role: str) -> ParticipantRole:
        normalized = role.strip().lower()
        if normalized in self._ALLOWED_ROLES:
            return normalized  # type: ignore[return-value]
        return "builder"
