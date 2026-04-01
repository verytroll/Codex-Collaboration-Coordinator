"""Operator shell bootstrap service."""

from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.models.api.artifacts import TranscriptExportResponse
from app.models.api.jobs import ApprovalRequestResponse, ArtifactResponse, JobResponse
from app.models.api.messages import MessageResponse
from app.models.api.operator_dashboard import OperatorDashboardFiltersResponse
from app.models.api.operator_ui import (
    OperatorSessionDetailResponse,
    OperatorSessionSummaryResponse,
    OperatorShellResponse,
)
from app.models.api.participants import ParticipantPolicyResponse, ParticipantResponse
from app.models.api.phases import PhaseResponse
from app.models.api.sessions import SessionResponse
from app.repositories.agents import AgentRepository
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import (
    MessageMentionRepository,
    MessageRecord,
    MessageRepository,
)
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.phases import PhaseRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.repositories.transcript_exports import (
    TranscriptExportRecord,
    TranscriptExportRepository,
)
from app.services.operator_dashboard import OperatorDashboardFilters, OperatorDashboardService
from app.services.participant_policy import ParticipantPolicyService

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class OperatorShellService:
    """Build the thin operator shell bootstrap payload."""

    def __init__(
        self,
        *,
        dashboard_service: OperatorDashboardService,
        session_repository: SessionRepository,
        phase_repository: PhaseRepository,
        job_repository: JobRepository,
        approval_repository: ApprovalRepository,
        artifact_repository: ArtifactRepository,
        transcript_export_repository: TranscriptExportRepository,
        message_repository: MessageRepository,
        message_mention_repository: MessageMentionRepository,
        participant_repository: ParticipantRepository,
        agent_repository: AgentRepository,
        participant_policy_service: ParticipantPolicyService,
    ) -> None:
        self.dashboard_service = dashboard_service
        self.session_repository = session_repository
        self.phase_repository = phase_repository
        self.job_repository = job_repository
        self.approval_repository = approval_repository
        self.artifact_repository = artifact_repository
        self.transcript_export_repository = transcript_export_repository
        self.message_repository = message_repository
        self.message_mention_repository = message_mention_repository
        self.participant_repository = participant_repository
        self.agent_repository = agent_repository
        self.participant_policy_service = participant_policy_service

    async def get_shell(
        self,
        filters: OperatorDashboardFilters | None = None,
        *,
        selected_session_id: str | None = None,
    ) -> OperatorShellResponse:
        """Return the operator shell bootstrap payload."""
        resolved_filters = filters or OperatorDashboardFilters()
        dashboard = await self.dashboard_service.get_dashboard(resolved_filters)
        sessions, phases, jobs, approvals, artifacts, transcripts, messages = await asyncio.gather(
            self.session_repository.list(),
            self.phase_repository.list(),
            self.job_repository.list(),
            self.approval_repository.list(),
            self.artifact_repository.list(),
            self.transcript_export_repository.list(),
            self.message_repository.list(),
        )
        selected_session = self._resolve_selected_session(
            sessions,
            phases,
            resolved_filters,
            requested_session_id=selected_session_id,
        )
        job_session_by_id = {job.id: job.session_id for job in jobs}
        counts_by_session = self._build_counts(
            sessions=sessions,
            phases=phases,
            jobs=jobs,
            approvals=approvals,
            artifacts=artifacts,
            messages=messages,
            job_session_by_id=job_session_by_id,
        )
        summaries = [
            self._session_summary(session, counts_by_session.get(session.id, Counter()))
            for session in sorted(sessions, key=self._session_sort_key, reverse=True)
        ]
        selected_detail = (
            await self._build_selected_detail(
                selected_session,
                phases=phases,
                jobs=jobs,
                approvals=approvals,
                artifacts=artifacts,
                transcripts=transcripts,
                messages=messages,
                job_session_by_id=job_session_by_id,
            )
            if selected_session is not None
            else None
        )
        payload = OperatorShellResponse(
            generated_at=_utc_now(),
            filters=OperatorDashboardFiltersResponse(
                session_id=resolved_filters.session_id,
                template_key=resolved_filters.template_key,
                phase_key=resolved_filters.phase_key,
                runtime_pool_key=resolved_filters.runtime_pool_key,
            ),
            dashboard=dashboard,
            sessions=summaries,
            selected_session_id=selected_session.id if selected_session is not None else None,
            selected_session=selected_detail,
        )
        logger.info(
            "operator shell bootstrap generated",
            extra={
                "selected_session_id": payload.selected_session_id,
                "session_count": len(payload.sessions),
            },
        )
        return payload

    def _build_counts(
        self,
        *,
        sessions: list[SessionRecord],
        phases: list[Any],
        jobs: list[JobRecord],
        approvals: list[ApprovalRequestRecord],
        artifacts: list[ArtifactRecord],
        messages: list[MessageRecord],
        job_session_by_id: dict[str, str],
    ) -> dict[str, Counter[str]]:
        counts_by_session: dict[str, Counter[str]] = defaultdict(Counter)
        for phase in phases:
            counts_by_session[phase.session_id]["phase_count"] += 1
        for message in messages:
            counts_by_session[message.session_id]["message_count"] += 1
        for job in jobs:
            counts_by_session[job.session_id]["job_count"] += 1
        for approval in approvals:
            session_id = job_session_by_id.get(approval.job_id)
            if session_id is not None:
                counts_by_session[session_id]["approval_count"] += 1
        for artifact in artifacts:
            counts_by_session[artifact.session_id]["artifact_count"] += 1
        for session in sessions:
            counts_by_session[session.id]["message_count"] += 0
        return counts_by_session

    def _session_summary(
        self,
        session: SessionRecord,
        counts: Counter[str],
    ) -> OperatorSessionSummaryResponse:
        return OperatorSessionSummaryResponse(
            session=self._session_response(session),
            template_key=session.template_key,
            loop_guard_status=session.loop_guard_status,
            loop_guard_reason=session.loop_guard_reason,
            last_message_at=session.last_message_at,
            phase_count=int(counts.get("phase_count", 0)),
            message_count=int(counts.get("message_count", 0)),
            job_count=int(counts.get("job_count", 0)),
            approval_count=int(counts.get("approval_count", 0)),
            artifact_count=int(counts.get("artifact_count", 0)),
        )

    async def _build_selected_detail(
        self,
        session: SessionRecord,
        *,
        phases: list[Any],
        jobs: list[JobRecord],
        approvals: list[ApprovalRequestRecord],
        artifacts: list[ArtifactRecord],
        transcripts: list[TranscriptExportRecord],
        messages: list[MessageRecord],
        job_session_by_id: dict[str, str],
    ) -> OperatorSessionDetailResponse:
        selected_phases = [phase for phase in phases if phase.session_id == session.id]
        selected_jobs = [job for job in jobs if job.session_id == session.id]
        selected_job_ids = {job.id for job in selected_jobs}
        selected_approvals = [
            approval for approval in approvals if approval.job_id in selected_job_ids
        ]
        selected_artifacts = [
            artifact for artifact in artifacts if artifact.session_id == session.id
        ]
        selected_transcripts = [
            transcript for transcript in transcripts if transcript.session_id == session.id
        ]
        selected_messages = [message for message in messages if message.session_id == session.id]
        mentions_by_message_id = await self._load_message_mentions(selected_messages)
        participants, agent_roles = await self._load_participants(session.id)
        selected_session = self._session_summary(
            session,
            self._build_counts(
                sessions=[session],
                phases=selected_phases,
                jobs=selected_jobs,
                approvals=selected_approvals,
                artifacts=selected_artifacts,
                messages=selected_messages,
                job_session_by_id=job_session_by_id,
            ).get(session.id, Counter()),
        )
        return OperatorSessionDetailResponse(
            **selected_session.model_dump(),
            phases=[
                self._phase_response(phase, active_phase_id=session.active_phase_id)
                for phase in selected_phases
            ],
            participants=[
                self._participant_response(
                    participant,
                    agent_role=agent_roles.get(participant.agent_id, participant.role),
                )
                for participant in participants
            ],
            messages=[
                self._message_response(
                    message,
                    mentions=mentions_by_message_id.get(message.id, []),
                )
                for message in selected_messages
            ],
            jobs=[self._job_response(job) for job in selected_jobs],
            approvals=[self._approval_response(approval) for approval in selected_approvals],
            artifacts=[self._artifact_response(artifact) for artifact in selected_artifacts],
            transcript_exports=[
                self._transcript_export_response(transcript) for transcript in selected_transcripts
            ],
        )

    async def _load_participants(
        self,
        session_id: str,
    ) -> tuple[list[SessionParticipantRecord], dict[str, str]]:
        participants, agents = await asyncio.gather(
            self.participant_repository.list_by_session(session_id),
            self.agent_repository.list(),
        )
        agent_roles = {agent.id: agent.role for agent in agents}
        return participants, agent_roles

    async def _load_message_mentions(
        self,
        messages: list[MessageRecord],
    ) -> dict[str, list[str]]:
        if not messages:
            return {}
        mentions = await asyncio.gather(
            *[
                self.message_mention_repository.list_by_message(message.id)
                for message in messages
            ]
        )
        return {
            message.id: [mention.mentioned_agent_id for mention in mention_rows]
            for message, mention_rows in zip(messages, mentions, strict=True)
        }

    def _resolve_selected_session(
        self,
        sessions: list[SessionRecord],
        phases: list[Any],
        filters: OperatorDashboardFilters,
        *,
        requested_session_id: str | None,
    ) -> SessionRecord | None:
        session_by_id = {session.id: session for session in sessions}
        if requested_session_id is not None:
            session = session_by_id.get(requested_session_id)
            if session is None:
                raise LookupError(f"Session not found: {requested_session_id}")
            return session
        filtered = list(sessions)
        if filters.template_key is not None:
            filtered = [
                session
                for session in filtered
                if session.template_key == filters.template_key
            ]
        if filters.phase_key is not None:
            active_phase_by_session_id = self._active_phase_key_by_session_id(phases, sessions)
            filtered = [
                session
                for session in filtered
                if active_phase_by_session_id.get(session.id) == filters.phase_key
            ]
        if filtered:
            return max(filtered, key=self._session_sort_key)
        if sessions:
            return max(sessions, key=self._session_sort_key)
        return None

    @staticmethod
    def _session_sort_key(session: SessionRecord) -> tuple[str, str, str]:
        return (session.updated_at, session.created_at, session.id)

    @staticmethod
    def _active_phase_key_by_session_id(
        phases: list[Any],
        sessions: list[SessionRecord],
    ) -> dict[str, str | None]:
        phases_by_id = {phase.id: phase for phase in phases}
        return {
            session.id: (
                phases_by_id[session.active_phase_id].phase_key
                if session.active_phase_id is not None and session.active_phase_id in phases_by_id
                else None
            )
            for session in sessions
        }

    @staticmethod
    def _session_response(session: SessionRecord) -> SessionResponse:
        return SessionResponse(
            id=session.id,
            title=session.title,
            goal=session.goal,
            status=session.status,
            lead_agent_id=session.lead_agent_id,
            active_phase_id=session.active_phase_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _phase_response(self, phase: Any, *, active_phase_id: str | None) -> PhaseResponse:
        return PhaseResponse(
            id=phase.id,
            session_id=phase.session_id,
            phase_key=phase.phase_key,
            title=phase.title,
            description=phase.description,
            relay_template_key=phase.relay_template_key,
            default_channel_key=phase.default_channel_key,
            sort_order=phase.sort_order,
            is_default=bool(phase.is_default),
            is_active=phase.id == active_phase_id,
            created_at=phase.created_at,
            updated_at=phase.updated_at,
        )

    def _participant_response(
        self,
        participant: SessionParticipantRecord,
        *,
        agent_role: str,
    ) -> ParticipantResponse:
        policy = self.participant_policy_service.resolve_policy(
            role=participant.role,
            policy_json=participant.policy_json,
            is_lead=participant.is_lead == 1,
        )
        return ParticipantResponse(
            session_id=participant.session_id,
            agent_id=participant.agent_id,
            agent_role=agent_role,
            role=participant.role,
            is_lead=bool(participant.is_lead),
            participant_status=participant.participant_status,
            joined_at=participant.joined_at or participant.created_at,
            read_scope=participant.read_scope,
            write_scope=participant.write_scope,
            policy=ParticipantPolicyResponse(**asdict(policy)),
        )

    @staticmethod
    def _message_response(
        message: MessageRecord,
        *,
        mentions: list[str] | None = None,
    ) -> MessageResponse:
        return MessageResponse(
            id=message.id,
            session_id=message.session_id,
            channel_key=message.channel_key,
            sender_type=message.sender_type,  # type: ignore[arg-type]
            sender_id=message.sender_id,
            content=message.content,
            message_type=message.message_type,  # type: ignore[arg-type]
            reply_to_message_id=message.reply_to_message_id,
            mentions=mentions or [],
            artifacts=[],
            created_at=message.created_at,
        )

    @staticmethod
    def _job_response(job: JobRecord) -> JobResponse:
        return JobResponse(
            id=job.id,
            session_id=job.session_id,
            channel_key=job.channel_key,
            assigned_agent_id=job.assigned_agent_id,
            runtime_id=job.runtime_id,
            source_message_id=job.source_message_id,
            parent_job_id=job.parent_job_id,
            title=job.title,
            instructions=job.instructions,
            status=job.status,  # type: ignore[arg-type]
            hop_count=job.hop_count,
            priority=job.priority,  # type: ignore[arg-type]
            codex_runtime_id=job.codex_runtime_id,
            codex_thread_id=job.codex_thread_id,
            active_turn_id=job.active_turn_id,
            last_known_turn_status=job.last_known_turn_status,
            result_summary=job.result_summary,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    @staticmethod
    def _approval_response(approval: ApprovalRequestRecord) -> ApprovalRequestResponse:
        return ApprovalRequestResponse(
            id=approval.id,
            job_id=approval.job_id,
            agent_id=approval.agent_id,
            approval_type=approval.approval_type,
            status=approval.status,
            request_payload=_parse_json(approval.request_payload_json) or {},
            decision_payload=_parse_json(approval.decision_payload_json),
            requested_at=approval.requested_at,
            resolved_at=approval.resolved_at,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
        )

    @staticmethod
    def _artifact_response(artifact: ArtifactRecord) -> ArtifactResponse:
        return ArtifactResponse(
            id=artifact.id,
            job_id=artifact.job_id,
            session_id=artifact.session_id,
            channel_key=artifact.channel_key,
            source_message_id=artifact.source_message_id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            content_text=artifact.content_text,
            file_path=artifact.file_path,
            file_name=artifact.file_name,
            mime_type=artifact.mime_type,
            size_bytes=artifact.size_bytes,
            checksum_sha256=artifact.checksum_sha256,
            metadata=_parse_json(artifact.metadata_json),
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    @staticmethod
    def _transcript_export_response(transcript: TranscriptExportRecord) -> TranscriptExportResponse:
        return TranscriptExportResponse(
            id=transcript.id,
            session_id=transcript.session_id,
            export_kind=transcript.export_kind,
            export_format=transcript.export_format,
            title=transcript.title,
            file_name=transcript.file_name,
            mime_type=transcript.mime_type,
            content_text=transcript.content_text,
            size_bytes=transcript.size_bytes,
            checksum_sha256=transcript.checksum_sha256,
            metadata=_parse_json(transcript.metadata_json),
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return data if isinstance(data, dict) else {"value": data}
