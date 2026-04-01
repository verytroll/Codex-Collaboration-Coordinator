"""Session templates and orchestration presets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.models.api.session_templates import (
    SessionTemplateChannelSpec,
    SessionTemplateCreateRequest,
    SessionTemplateOrchestrationSpec,
    SessionTemplatePhaseSpec,
    SessionTemplateRulePresetSpec,
)
from app.repositories.agents import AgentRepository
from app.repositories.channels import SessionChannelRecord, SessionChannelRepository
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.session_templates import SessionTemplateRecord, SessionTemplateRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.channel_service import DEFAULT_CHANNELS
from app.services.phase_service import PhaseService
from app.services.rule_engine import RuleEngineService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SessionTemplateDefinition:
    """Resolved session template definition."""

    id: str
    template_key: str
    title: str
    description: str | None
    default_goal: str | None
    participant_roles: tuple[str, ...]
    channels: tuple[SessionTemplateChannelSpec, ...]
    phase_order: tuple[SessionTemplatePhaseSpec, ...]
    rule_presets: tuple[SessionTemplateRulePresetSpec, ...]
    orchestration: SessionTemplateOrchestrationSpec | None
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str


class SessionTemplateService:
    """Manage session templates and instantiate sessions from presets."""

    _BUILTIN_TEMPLATE_KEYS = (
        "planning_heavy",
        "implementation_review",
        "research_review",
        "hotfix_triage",
    )
    _BUILTIN_TEMPLATES: tuple[SessionTemplateDefinition, ...] = (
        SessionTemplateDefinition(
            id="tpl_builtin_planning_heavy",
            template_key="planning_heavy",
            title="Planning Heavy",
            description=(
                "Structured planning-first collaboration with explicit planning and review lanes."
            ),
            default_goal="Clarify scope, risks, and handoff direction before implementation.",
            participant_roles=("planner", "builder", "reviewer"),
            channels=(
                SessionTemplateChannelSpec(
                    channel_key="general",
                    display_name="General",
                    description="Default coordination channel",
                    sort_order=10,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="planning",
                    display_name="Planning",
                    description="Planning and scoping",
                    sort_order=20,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="review",
                    display_name="Review",
                    description="Review and feedback",
                    sort_order=30,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="debug",
                    display_name="Debug",
                    description="Operator diagnostics and debugging",
                    sort_order=40,
                    is_default=True,
                ),
            ),
            phase_order=(
                SessionTemplatePhaseSpec(phase_key="planning", sort_order=10),
                SessionTemplatePhaseSpec(phase_key="implementation", sort_order=20),
                SessionTemplatePhaseSpec(phase_key="review", sort_order=30),
                SessionTemplatePhaseSpec(phase_key="revise", sort_order=40),
                SessionTemplatePhaseSpec(phase_key="finalize", sort_order=50),
            ),
            rule_presets=(
                SessionTemplateRulePresetSpec(
                    rule_type="channel_routing_preference",
                    name="Keep general traffic in planning",
                    description="Route general mentions into planning while the session is scoped.",
                    priority=10,
                    is_active=True,
                    conditions={"channel_key": "general"},
                    actions={"target_channel_key": "planning"},
                ),
            ),
            orchestration=SessionTemplateOrchestrationSpec(default_active_phase_key="planning"),
            is_default=True,
            sort_order=10,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
        SessionTemplateDefinition(
            id="tpl_builtin_implementation_review",
            template_key="implementation_review",
            title="Implementation Review",
            description=(
                "Implementation-first collaboration with a review checkpoint before finalize."
            ),
            default_goal="Build the feature, review the changes, and finalize safely.",
            participant_roles=("planner", "builder", "reviewer"),
            channels=(
                SessionTemplateChannelSpec(
                    channel_key="general",
                    display_name="General",
                    description="Default coordination channel",
                    sort_order=10,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="planning",
                    display_name="Planning",
                    description="Planning and scoping",
                    sort_order=20,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="review",
                    display_name="Review",
                    description="Review and feedback",
                    sort_order=30,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="debug",
                    display_name="Debug",
                    description="Operator diagnostics and debugging",
                    sort_order=40,
                    is_default=True,
                ),
            ),
            phase_order=(
                SessionTemplatePhaseSpec(phase_key="planning", sort_order=10),
                SessionTemplatePhaseSpec(phase_key="implementation", sort_order=20),
                SessionTemplatePhaseSpec(phase_key="review", sort_order=30),
                SessionTemplatePhaseSpec(phase_key="revise", sort_order=40),
                SessionTemplatePhaseSpec(phase_key="finalize", sort_order=50),
            ),
            rule_presets=(
                SessionTemplateRulePresetSpec(
                    rule_type="review_required",
                    name="Review checkpoint",
                    description="Keep review work gated until the review phase is active.",
                    priority=10,
                    is_active=True,
                    conditions={"channel_key": "review"},
                    actions={"hold": True},
                ),
            ),
            orchestration=SessionTemplateOrchestrationSpec(
                default_active_phase_key="implementation"
            ),
            is_default=False,
            sort_order=20,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
        SessionTemplateDefinition(
            id="tpl_builtin_research_review",
            template_key="research_review",
            title="Research Review",
            description="Research-heavy collaboration with an explicit research lane and review.",
            default_goal="Gather findings, compare options, and review the conclusion.",
            participant_roles=("planner", "researcher", "reviewer"),
            channels=(
                SessionTemplateChannelSpec(
                    channel_key="general",
                    display_name="General",
                    description="Default coordination channel",
                    sort_order=10,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="planning",
                    display_name="Planning",
                    description="Planning and scoping",
                    sort_order=20,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="research",
                    display_name="Research",
                    description="Research and discovery",
                    sort_order=25,
                    is_default=False,
                ),
                SessionTemplateChannelSpec(
                    channel_key="review",
                    display_name="Review",
                    description="Review and feedback",
                    sort_order=30,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="debug",
                    display_name="Debug",
                    description="Operator diagnostics and debugging",
                    sort_order=40,
                    is_default=True,
                ),
            ),
            phase_order=(
                SessionTemplatePhaseSpec(phase_key="planning", sort_order=10),
                SessionTemplatePhaseSpec(phase_key="implementation", sort_order=20),
                SessionTemplatePhaseSpec(phase_key="review", sort_order=30),
                SessionTemplatePhaseSpec(phase_key="revise", sort_order=40),
                SessionTemplatePhaseSpec(phase_key="finalize", sort_order=50),
            ),
            rule_presets=(
                SessionTemplateRulePresetSpec(
                    rule_type="channel_routing_preference",
                    name="Send general mentions to research",
                    description="Route general mentions into research during discovery.",
                    priority=10,
                    is_active=True,
                    conditions={"channel_key": "general"},
                    actions={"target_channel_key": "research"},
                ),
            ),
            orchestration=SessionTemplateOrchestrationSpec(default_active_phase_key="planning"),
            is_default=False,
            sort_order=30,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
        SessionTemplateDefinition(
            id="tpl_builtin_hotfix_triage",
            template_key="hotfix_triage",
            title="Hotfix Triage",
            description="Urgent incident flow optimized for triage and quick review.",
            default_goal="Triage the issue, land the smallest safe fix, and verify it quickly.",
            participant_roles=("planner", "builder", "tester", "reviewer"),
            channels=(
                SessionTemplateChannelSpec(
                    channel_key="general",
                    display_name="General",
                    description="Default coordination channel",
                    sort_order=10,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="planning",
                    display_name="Planning",
                    description="Planning and scoping",
                    sort_order=20,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="hotfix",
                    display_name="Hotfix",
                    description="Incident triage and fix lane",
                    sort_order=25,
                    is_default=False,
                ),
                SessionTemplateChannelSpec(
                    channel_key="review",
                    display_name="Review",
                    description="Review and feedback",
                    sort_order=30,
                    is_default=True,
                ),
                SessionTemplateChannelSpec(
                    channel_key="debug",
                    display_name="Debug",
                    description="Operator diagnostics and debugging",
                    sort_order=40,
                    is_default=True,
                ),
            ),
            phase_order=(
                SessionTemplatePhaseSpec(phase_key="planning", sort_order=10),
                SessionTemplatePhaseSpec(phase_key="implementation", sort_order=20),
                SessionTemplatePhaseSpec(phase_key="review", sort_order=30),
                SessionTemplatePhaseSpec(phase_key="revise", sort_order=40),
                SessionTemplatePhaseSpec(phase_key="finalize", sort_order=50),
            ),
            rule_presets=(
                SessionTemplateRulePresetSpec(
                    rule_type="channel_routing_preference",
                    name="Route general mentions to hotfix",
                    description="Send general coordination into the hotfix lane during triage.",
                    priority=10,
                    is_active=True,
                    conditions={"channel_key": "general"},
                    actions={"target_channel_key": "hotfix"},
                ),
            ),
            orchestration=SessionTemplateOrchestrationSpec(default_active_phase_key="planning"),
            is_default=False,
            sort_order=40,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
    )

    def __init__(
        self,
        *,
        session_template_repository: SessionTemplateRepository,
        session_repository: SessionRepository,
        channel_repository: SessionChannelRepository,
        phase_repository: PhaseRepository,
        agent_repository: AgentRepository,
        phase_service: PhaseService,
        rule_engine_service: RuleEngineService,
    ) -> None:
        self.session_template_repository = session_template_repository
        self.session_repository = session_repository
        self.channel_repository = channel_repository
        self.phase_repository = phase_repository
        self.agent_repository = agent_repository
        self.phase_service = phase_service
        self.rule_engine_service = rule_engine_service

    def list_builtin_templates(self) -> list[SessionTemplateDefinition]:
        """Return the built-in template catalog."""
        return list(self._BUILTIN_TEMPLATES)

    def _builtin_template_keys(self) -> set[str]:
        return {template.template_key for template in self._BUILTIN_TEMPLATES}

    async def list_templates(self) -> list[SessionTemplateDefinition]:
        """Return built-in and stored templates."""
        stored_templates = [
            self._record_to_definition(record)
            for record in await self.session_template_repository.list()
        ]
        return [*self.list_builtin_templates(), *stored_templates]

    async def get_template(self, template_key: str) -> SessionTemplateDefinition:
        """Return a template definition by key."""
        for template in self._BUILTIN_TEMPLATES:
            if template.template_key == template_key:
                return template
        record = await self.session_template_repository.get_by_key(template_key)
        if record is None:
            raise LookupError(f"Session template not found: {template_key}")
        return self._record_to_definition(record)

    async def create_template(
        self, payload: SessionTemplateCreateRequest
    ) -> SessionTemplateDefinition:
        """Create a custom session template."""
        if payload.template_key in self._builtin_template_keys():
            raise ValueError(f"Template key is reserved for built-ins: {payload.template_key}")
        if await self.session_template_repository.get_by_key(payload.template_key) is not None:
            raise ValueError(f"Session template already exists: {payload.template_key}")

        normalized_channels = self._normalize_channels(payload.channels)
        normalized_phases = self._normalize_phases(payload.phase_order)
        now = _utc_now()
        record = SessionTemplateRecord(
            id=f"tpl_{uuid4().hex}",
            template_key=payload.template_key,
            title=payload.title,
            description=payload.description,
            default_goal=payload.default_goal,
            participant_roles_json=json.dumps(payload.participant_roles, sort_keys=True),
            channels_json=json.dumps(
                [channel.model_dump() for channel in normalized_channels], sort_keys=True
            ),
            phase_order_json=json.dumps(
                [phase.model_dump() for phase in normalized_phases], sort_keys=True
            ),
            rule_presets_json=json.dumps(
                [rule.model_dump() for rule in payload.rule_presets],
                sort_keys=True,
            ),
            orchestration_json=(
                json.dumps(payload.orchestration.model_dump(), sort_keys=True)
                if payload.orchestration is not None
                else None
            ),
            is_default=1 if payload.is_default else 0,
            sort_order=payload.sort_order,
            created_at=now,
            updated_at=now,
        )
        saved = await self.session_template_repository.create(record)
        return self._record_to_definition(saved)

    async def instantiate_session(
        self,
        template_key: str,
        *,
        title: str | None = None,
        goal: str | None = None,
        lead_agent_id: str | None = None,
    ) -> SessionRecord:
        """Create a session from a template and apply orchestration presets."""
        template = await self.get_template(template_key)
        if lead_agent_id is not None and await self.agent_repository.get(lead_agent_id) is None:
            raise LookupError(f"Agent not found: {lead_agent_id}")

        now = _utc_now()
        session = SessionRecord(
            id=f"ses_{uuid4().hex}",
            title=title or template.title,
            goal=goal if goal is not None else template.default_goal,
            status="active" if lead_agent_id is not None else "draft",
            lead_agent_id=lead_agent_id,
            active_phase_id=None,
            loop_guard_status="normal",
            loop_guard_reason=None,
            last_message_at=None,
            created_at=now,
            updated_at=now,
        )
        created_session = await self.session_repository.create(session)

        channel_definitions = self._resolve_channels(template.channels)
        await self._seed_channels(created_session.id, channel_definitions, now=now)

        phase_keys = self._resolve_phase_order(template.phase_order)
        active_phase_key = self._resolve_active_phase_key(template, phase_keys)
        phase_records = await self._seed_phases(
            created_session.id,
            phase_keys,
            active_phase_key=active_phase_key,
            now=now,
        )
        await self._seed_rules(created_session.id, template.rule_presets)

        active_phase = next(
            (phase for phase in phase_records if phase.phase_key == active_phase_key),
            phase_records[0] if phase_records else None,
        )
        if active_phase is None:
            return created_session

        return await self.session_repository.update(
            SessionRecord(
                id=created_session.id,
                title=created_session.title,
                goal=created_session.goal,
                status=created_session.status,
                lead_agent_id=created_session.lead_agent_id,
                active_phase_id=active_phase.id,
                loop_guard_status=created_session.loop_guard_status,
                loop_guard_reason=created_session.loop_guard_reason,
                last_message_at=created_session.last_message_at,
                created_at=created_session.created_at,
                updated_at=now,
            )
        )

    async def _seed_channels(
        self,
        session_id: str,
        channels: tuple[SessionTemplateChannelSpec, ...],
        *,
        now: str,
    ) -> None:
        existing = await self.channel_repository.list_by_session(session_id)
        existing_keys = {channel.channel_key for channel in existing}
        for channel in channels:
            if channel.channel_key in existing_keys:
                continue
            await self.channel_repository.create(
                SessionChannelRecord(
                    id=f"chn_{uuid4().hex}",
                    session_id=session_id,
                    channel_key=channel.channel_key,
                    display_name=channel.display_name,
                    description=channel.description,
                    is_default=channel.is_default,
                    sort_order=channel.sort_order,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _seed_phases(
        self,
        session_id: str,
        phase_keys: list[str],
        *,
        active_phase_key: str | None,
        now: str,
    ) -> list[PhaseRecord]:
        existing = await self.phase_repository.list_by_session(session_id)
        existing_keys = {phase.phase_key for phase in existing}
        created: list[PhaseRecord] = []
        for sort_index, phase_key in enumerate(phase_keys, start=1):
            if phase_key in existing_keys:
                continue
            preset = self.phase_service.get_preset(phase_key)
            created.append(
                await self.phase_repository.create(
                    PhaseRecord(
                        id=f"ph_{uuid4().hex}",
                        session_id=session_id,
                        phase_key=preset.phase_key,
                        title=preset.title,
                        description=preset.description,
                        relay_template_key=preset.relay_template_key,
                        default_channel_key=preset.default_channel_key,
                        sort_order=sort_index * 10,
                        is_default=1 if phase_key == active_phase_key else 0,
                        created_at=now,
                        updated_at=now,
                    )
                )
            )
        return sorted(
            [*existing, *created], key=lambda phase: (phase.sort_order, phase.created_at, phase.id)
        )

    async def _seed_rules(
        self,
        session_id: str,
        rule_presets: tuple[SessionTemplateRulePresetSpec, ...],
    ) -> None:
        existing_rules = await self.rule_engine_service.list_rules(session_id)
        existing_names = {rule.name for rule in existing_rules}
        for rule_preset in rule_presets:
            if rule_preset.name in existing_names:
                continue
            await self.rule_engine_service.create_rule(
                session_id=session_id,
                rule_type=rule_preset.rule_type,
                name=rule_preset.name,
                description=rule_preset.description,
                priority=rule_preset.priority,
                is_active=rule_preset.is_active,
                conditions=rule_preset.conditions,
                actions=rule_preset.actions,
            )

    def _record_to_definition(self, record: SessionTemplateRecord) -> SessionTemplateDefinition:
        orchestration = self._parse_orchestration(record.orchestration_json)
        return SessionTemplateDefinition(
            id=record.id,
            template_key=record.template_key,
            title=record.title,
            description=record.description,
            default_goal=record.default_goal,
            participant_roles=tuple(self._parse_string_list(record.participant_roles_json)),
            channels=tuple(self._parse_channel_specs(record.channels_json)),
            phase_order=tuple(self._parse_phase_specs(record.phase_order_json)),
            rule_presets=tuple(self._parse_rule_specs(record.rule_presets_json)),
            orchestration=orchestration,
            is_default=bool(record.is_default),
            sort_order=record.sort_order,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _resolve_channels(
        self,
        channels: tuple[SessionTemplateChannelSpec, ...],
    ) -> tuple[SessionTemplateChannelSpec, ...]:
        base_channels = [
            SessionTemplateChannelSpec(
                channel_key=channel_key,
                display_name=display_name,
                description=description,
                sort_order=sort_order,
                is_default=True,
            )
            for channel_key, display_name, description, sort_order in DEFAULT_CHANNELS
        ]
        resolved_by_key = {channel.channel_key: channel for channel in base_channels}
        for channel in channels:
            resolved_by_key[channel.channel_key] = channel
        return tuple(
            sorted(
                resolved_by_key.values(),
                key=lambda channel: (channel.sort_order, channel.channel_key),
            )
        )

    def _resolve_phase_order(self, phase_order: tuple[SessionTemplatePhaseSpec, ...]) -> list[str]:
        base_order = [preset.phase_key for preset in self.phase_service.list_presets()]
        requested = [phase.phase_key for phase in phase_order if phase.phase_key in base_order]
        resolved: list[str] = []
        for phase_key in [*requested, *base_order]:
            if phase_key not in resolved:
                resolved.append(phase_key)
        return resolved

    def _resolve_active_phase_key(
        self,
        template: SessionTemplateDefinition,
        phase_keys: list[str],
    ) -> str | None:
        if template.orchestration is not None:
            active_phase_key = template.orchestration.default_active_phase_key
            if isinstance(active_phase_key, str) and active_phase_key in phase_keys:
                return active_phase_key
        return phase_keys[0] if phase_keys else None

    @staticmethod
    def _normalize_channels(
        channels: list[SessionTemplateChannelSpec],
    ) -> list[SessionTemplateChannelSpec]:
        normalized: list[SessionTemplateChannelSpec] = []
        for index, channel in enumerate(channels, start=1):
            normalized.append(
                channel.model_copy(
                    update={
                        "sort_order": channel.sort_order if channel.sort_order > 0 else index * 10,
                    }
                )
            )
        return normalized

    @staticmethod
    def _normalize_phases(
        phases: list[SessionTemplatePhaseSpec],
    ) -> list[SessionTemplatePhaseSpec]:
        normalized: list[SessionTemplatePhaseSpec] = []
        for index, phase in enumerate(phases, start=1):
            normalized.append(
                phase.model_copy(
                    update={"sort_order": phase.sort_order if phase.sort_order > 0 else index * 10}
                )
            )
        return normalized

    @staticmethod
    def _parse_string_list(payload_json: str) -> list[str]:
        payload = json.loads(payload_json)
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

    @staticmethod
    def _parse_channel_specs(payload_json: str) -> list[SessionTemplateChannelSpec]:
        payload = json.loads(payload_json)
        if not isinstance(payload, list):
            return []
        return [
            SessionTemplateChannelSpec(
                channel_key=item["channel_key"],
                display_name=item["display_name"],
                description=item.get("description"),
                sort_order=item.get("sort_order", 0),
                is_default=bool(item.get("is_default", False)),
            )
            for item in payload
            if isinstance(item, dict)
            and isinstance(item.get("channel_key"), str)
            and isinstance(item.get("display_name"), str)
        ]

    @staticmethod
    def _parse_phase_specs(payload_json: str) -> list[SessionTemplatePhaseSpec]:
        payload = json.loads(payload_json)
        if not isinstance(payload, list):
            return []
        return [
            SessionTemplatePhaseSpec(
                phase_key=item["phase_key"],
                sort_order=item.get("sort_order", 0),
            )
            for item in payload
            if isinstance(item, dict) and isinstance(item.get("phase_key"), str)
        ]

    @staticmethod
    def _parse_rule_specs(payload_json: str) -> list[SessionTemplateRulePresetSpec]:
        payload = json.loads(payload_json)
        if not isinstance(payload, list):
            return []
        return [
            SessionTemplateRulePresetSpec(
                rule_type=item["rule_type"],
                name=item["name"],
                description=item.get("description"),
                priority=item.get("priority", 100),
                is_active=bool(item.get("is_active", False)),
                conditions=item.get("conditions")
                if isinstance(item.get("conditions"), dict)
                else None,
                actions=item.get("actions") if isinstance(item.get("actions"), dict) else None,
            )
            for item in payload
            if isinstance(item, dict)
            and isinstance(item.get("rule_type"), str)
            and isinstance(item.get("name"), str)
        ]

    @staticmethod
    def _parse_orchestration(
        payload_json: str | None,
    ) -> SessionTemplateOrchestrationSpec | None:
        if payload_json is None:
            return None
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            return None
        default_active_phase_key = payload.get("default_active_phase_key")
        return SessionTemplateOrchestrationSpec(
            default_active_phase_key=default_active_phase_key
            if isinstance(default_active_phase_key, str)
            else None
        )
