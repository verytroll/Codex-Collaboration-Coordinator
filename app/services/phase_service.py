"""Phase presets and session phase orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.relay_templates import RelayTemplatesService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class PhasePresetDefinition:
    """Static preset definition for a session phase."""

    phase_key: str
    title: str
    description: str | None
    relay_template_key: str
    default_channel_key: str
    sort_order: int
    is_default: bool


@dataclass(frozen=True, slots=True)
class PhaseActivationResult:
    """Result from activating a session phase."""

    session: SessionRecord
    phase: PhaseRecord


class PhaseService:
    """Manage phase presets and active phase state."""

    _PRESETS: tuple[PhasePresetDefinition, ...] = (
        PhasePresetDefinition(
            phase_key="planning",
            title="Planning",
            description="Capture goals, scope, and handoff direction before implementation.",
            relay_template_key="planner_to_builder",
            default_channel_key="planning",
            sort_order=10,
            is_default=True,
        ),
        PhasePresetDefinition(
            phase_key="implementation",
            title="Implementation",
            description="Carry out the work and keep the session on the execution track.",
            relay_template_key="planner_to_builder",
            default_channel_key="general",
            sort_order=20,
            is_default=False,
        ),
        PhasePresetDefinition(
            phase_key="review",
            title="Review",
            description="Review the current work and capture structured feedback.",
            relay_template_key="builder_to_reviewer",
            default_channel_key="review",
            sort_order=30,
            is_default=False,
        ),
        PhasePresetDefinition(
            phase_key="revise",
            title="Revise",
            description="Apply review feedback and prepare the next implementation pass.",
            relay_template_key="reviewer_to_builder_revise",
            default_channel_key="review",
            sort_order=40,
            is_default=False,
        ),
        PhasePresetDefinition(
            phase_key="finalize",
            title="Finalize",
            description="Wrap up the work and prepare the session for completion.",
            relay_template_key="builder_to_reviewer",
            default_channel_key="general",
            sort_order=50,
            is_default=False,
        ),
    )

    def __init__(
        self,
        *,
        phase_repository: PhaseRepository,
        session_repository: SessionRepository,
        relay_templates_service: RelayTemplatesService,
    ) -> None:
        self.phase_repository = phase_repository
        self.session_repository = session_repository
        self.relay_templates_service = relay_templates_service

    def list_presets(self) -> list[PhasePresetDefinition]:
        """Return the supported phase presets."""
        return list(self._PRESETS)

    def get_preset(self, phase_key: str) -> PhasePresetDefinition:
        """Return a preset definition by key."""
        for preset in self._PRESETS:
            if preset.phase_key == phase_key:
                return preset
        raise LookupError(f"Unknown phase preset: {phase_key}")

    async def ensure_default_phases(self, session_id: str) -> list[PhaseRecord]:
        """Create missing preset rows for a session."""
        await self._get_session(session_id)
        existing = await self.phase_repository.list_by_session(session_id)
        existing_by_key = {phase.phase_key: phase for phase in existing}
        created: list[PhaseRecord] = []
        for preset in self._PRESETS:
            if preset.phase_key in existing_by_key:
                continue
            now = _utc_now()
            phase = await self.phase_repository.create(
                PhaseRecord(
                    id=f"ph_{uuid4().hex}",
                    session_id=session_id,
                    phase_key=preset.phase_key,
                    title=preset.title,
                    description=preset.description,
                    relay_template_key=preset.relay_template_key,
                    default_channel_key=preset.default_channel_key,
                    sort_order=preset.sort_order,
                    is_default=1 if preset.is_default else 0,
                    created_at=now,
                    updated_at=now,
                )
            )
            created.append(phase)
        return self._sort_phases([*existing, *created])

    async def list_phases(self, session_id: str) -> list[PhaseRecord]:
        """Return all phases for a session, seeding presets if necessary."""
        await self._get_session(session_id)
        phases = await self.phase_repository.list_by_session(session_id)
        if phases:
            return self._sort_phases(phases)
        return await self.ensure_default_phases(session_id)

    async def get_phase(self, phase_id: str) -> PhaseRecord | None:
        """Return a phase row by id."""
        return await self.phase_repository.get(phase_id)

    async def get_phase_by_key(
        self,
        session_id: str,
        phase_key: str,
    ) -> PhaseRecord | None:
        """Return a phase row by session and key."""
        return await self.phase_repository.get_by_session_and_key(session_id, phase_key)

    async def get_active_phase(self, session_id: str) -> PhaseRecord | None:
        """Return the active phase for a session, or the default preset."""
        await self._get_session(session_id)
        await self.ensure_default_phases(session_id)
        session = await self._get_session(session_id)
        if session.active_phase_id is not None:
            active_phase = await self.phase_repository.get(session.active_phase_id)
            if active_phase is not None and active_phase.session_id == session_id:
                return active_phase
        default_phase = await self.phase_repository.get_by_session_and_key(session_id, "planning")
        if default_phase is not None:
            return default_phase
        phases = await self.phase_repository.list_by_session(session_id)
        return phases[0] if phases else None

    async def activate_phase_by_key(
        self,
        session_id: str,
        phase_key: str,
    ) -> PhaseActivationResult:
        """Mark a phase preset as active for a session."""
        await self.ensure_default_phases(session_id)
        phase = await self.phase_repository.get_by_session_and_key(session_id, phase_key)
        if phase is None:
            raise LookupError(f"Phase not found in session {session_id}: {phase_key}")
        return await self._activate_phase(session_id=session_id, phase=phase)

    async def activate_phase_by_id(
        self,
        session_id: str,
        phase_id: str,
    ) -> PhaseActivationResult:
        """Mark a phase row as active for a session."""
        await self.ensure_default_phases(session_id)
        phase = await self.phase_repository.get(phase_id)
        if phase is None or phase.session_id != session_id:
            raise LookupError(f"Phase not found in session {session_id}: {phase_id}")
        return await self._activate_phase(session_id=session_id, phase=phase)

    async def build_new_job_instructions(
        self,
        *,
        session_id: str,
        objective: str,
        source_role: str | None,
        target_role: str | None,
        notes: str | None = None,
    ) -> str:
        """Render phase-aware instructions for a direct job command."""
        phase = await self.get_active_phase(session_id)
        resolved_phase = phase or self.get_preset("planning")
        payload = self._build_phase_payload(
            phase_key=resolved_phase.phase_key,
            phase_title=resolved_phase.title,
            relay_template_key=resolved_phase.relay_template_key,
            default_channel_key=resolved_phase.default_channel_key,
            objective=objective,
            source_role=source_role,
            target_role=target_role,
            notes=notes,
            session_id=session_id,
            phase_id=phase.id if phase is not None else None,
        )
        return self.relay_templates_service.render_markdown(payload)

    def list_preset_payloads(self) -> list[dict[str, object]]:
        """Return presets as JSON-friendly dictionaries."""
        return [
            {
                "phase_key": preset.phase_key,
                "title": preset.title,
                "description": preset.description,
                "relay_template_key": preset.relay_template_key,
                "default_channel_key": preset.default_channel_key,
                "sort_order": preset.sort_order,
                "is_default": preset.is_default,
            }
            for preset in self._PRESETS
        ]

    def _build_phase_payload(
        self,
        *,
        phase_key: str,
        phase_title: str,
        relay_template_key: str,
        default_channel_key: str,
        objective: str,
        source_role: str | None,
        target_role: str | None,
        notes: str | None,
        session_id: str,
        phase_id: str | None,
    ) -> dict[str, object]:
        if phase_key == "review":
            sections = {
                "completed_work": objective,
                "files_changed": [],
                "tests_run": [],
                "open_questions": [],
                "review_focus": notes,
            }
        elif phase_key == "revise":
            sections = {
                "decision": "changes_requested",
                "summary": objective,
                "required_changes": [],
                "revision_priority": "normal",
                "next_actions": [],
            }
        else:
            sections = {
                "objective": objective,
                "scope": None,
                "acceptance_criteria": [],
                "constraints": [],
                "notes": notes,
            }

        return {
            "template_key": relay_template_key,
            "title": phase_title,
            "source_role": source_role or "planner",
            "target_role": target_role or "builder",
            "channel_key": default_channel_key,
            "summary": f"{phase_title} phase handoff",
            "sections": sections,
            "metadata": {
                "session_id": session_id,
                "phase_id": phase_id,
                "phase_key": phase_key,
                "phase_title": phase_title,
                "source_role": source_role or "planner",
                "target_role": target_role or "builder",
            },
        }

    async def _activate_phase(
        self,
        *,
        session_id: str,
        phase: PhaseRecord,
    ) -> PhaseActivationResult:
        session = await self._get_session(session_id)
        updated_session = SessionRecord(
            id=session.id,
            title=session.title,
            goal=session.goal,
            status=session.status,
            lead_agent_id=session.lead_agent_id,
            active_phase_id=phase.id,
            loop_guard_status=session.loop_guard_status,
            loop_guard_reason=session.loop_guard_reason,
            last_message_at=session.last_message_at,
            template_key=session.template_key,
            created_at=session.created_at,
            updated_at=_utc_now(),
        )
        saved_session = await self.session_repository.update(updated_session)
        return PhaseActivationResult(session=saved_session, phase=phase)

    @staticmethod
    def _sort_phases(phases: list[PhaseRecord]) -> list[PhaseRecord]:
        return sorted(phases, key=lambda phase: (phase.sort_order, phase.created_at, phase.id))

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session
