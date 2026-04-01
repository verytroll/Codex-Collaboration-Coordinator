"""Review mode orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import MessageRecord, MessageRepository
from app.repositories.participants import ParticipantRepository
from app.repositories.reviews import ReviewRecord, ReviewRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.artifact_manager import ArtifactManager
from app.services.channel_service import ChannelService
from app.services.job_service import JobService
from app.services.offline_queue import OfflineQueueService
from app.services.relay_templates import RelayTemplateDefinition, RelayTemplatesService
from app.services.session_events import record_session_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, object]:
    if payload is None:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _reviewer_summary(artifacts: list[ArtifactRecord]) -> list[dict[str, object]]:
    return [
        {
            "id": artifact.id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "file_name": artifact.file_name,
            "mime_type": artifact.mime_type,
            "size_bytes": artifact.size_bytes,
        }
        for artifact in artifacts
    ]


@dataclass(frozen=True, slots=True)
class ReviewStartResult:
    """Result from starting a review."""

    review: ReviewRecord
    request_message: MessageRecord


@dataclass(frozen=True, slots=True)
class ReviewDecisionResult:
    """Result from recording a review decision."""

    review: ReviewRecord
    decision_message: MessageRecord
    summary_artifact: ArtifactRecord
    revision_job: JobRecord | None


class ReviewModeService:
    """Orchestrate review requests and decisions."""

    def __init__(
        self,
        *,
        review_repository: ReviewRepository,
        job_repository: JobRepository,
        message_repository: MessageRepository,
        artifact_repository: ArtifactRepository,
        artifact_manager: ArtifactManager,
        job_service: JobService,
        offline_queue_service: OfflineQueueService,
        session_repository: SessionRepository,
        participant_repository: ParticipantRepository,
        channel_service: ChannelService,
        session_event_repository: SessionEventRepository,
        relay_templates_service: RelayTemplatesService,
    ) -> None:
        self.review_repository = review_repository
        self.job_repository = job_repository
        self.message_repository = message_repository
        self.artifact_repository = artifact_repository
        self.artifact_manager = artifact_manager
        self.job_service = job_service
        self.offline_queue_service = offline_queue_service
        self.session_repository = session_repository
        self.participant_repository = participant_repository
        self.channel_service = channel_service
        self.session_event_repository = session_event_repository
        self.relay_templates_service = relay_templates_service

    async def list_templates(self) -> list[RelayTemplateDefinition]:
        """Return available structured relay templates."""
        return self.relay_templates_service.list_templates()

    async def get_template(self, template_key: str) -> RelayTemplateDefinition:
        """Return a template definition by key."""
        return self.relay_templates_service.get_template(template_key)

    async def list_reviews(self, session_id: str) -> list[ReviewRecord]:
        """Return review records for a session."""
        return await self.review_repository.list_by_session(session_id)

    async def get_review(self, review_id: str) -> ReviewRecord | None:
        """Return a review record by id."""
        return await self.review_repository.get(review_id)

    async def request_review(
        self,
        *,
        source_job_id: str,
        reviewer_agent_id: str | None = None,
        requested_by_agent_id: str | None = None,
        review_scope: str = "job",
        review_channel_key: str = "review",
        notes: str | None = None,
        policy_metadata: dict[str, object] | None = None,
    ) -> ReviewStartResult:
        """Create a review request for a job."""
        job = await self._get_job(source_job_id)
        session = await self._get_session(job.session_id)
        await self.channel_service.ensure_channel_exists(
            session_id=session.id,
            channel_key=review_channel_key,
        )
        if await self._has_active_review(job.id):
            raise ValueError(f"Job {job.id} already has an active review")

        resolved_reviewer_id = await self._resolve_reviewer_agent(
            session=session,
            explicit_reviewer_agent_id=reviewer_agent_id,
        )
        artifacts = await self.artifact_repository.list_by_job(job.id)
        request_payload = self.relay_templates_service.build_builder_to_reviewer(
            job_id=job.id,
            job_title=job.title,
            job_status=job.status,
            assigned_agent_id=job.assigned_agent_id,
            reviewer_agent_id=resolved_reviewer_id,
            completed_work=job.result_summary or job.instructions or job.title,
            files_changed=_reviewer_summary(artifacts),
            tests_run=[],
            open_questions=[],
            review_focus=notes,
            notes=notes,
        )
        if policy_metadata is not None:
            request_payload["policy_metadata"] = policy_metadata
        now = _utc_now()
        review = await self.review_repository.create(
            ReviewRecord(
                id=f"rvw_{uuid4().hex}",
                session_id=job.session_id,
                source_job_id=job.id,
                reviewer_agent_id=resolved_reviewer_id,
                requested_by_agent_id=requested_by_agent_id,
                review_scope=review_scope,
                review_status="requested",
                review_channel_key=review_channel_key,
                template_key="builder_to_reviewer",
                request_message_id=None,
                decision_message_id=None,
                summary_artifact_id=None,
                revision_job_id=None,
                request_payload_json=json.dumps(request_payload, sort_keys=True),
                decision_payload_json=None,
                requested_at=now,
                decided_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        request_message = await self._publish_message(
            session=session,
            sender_type="agent" if requested_by_agent_id is not None else "system",
            sender_id=requested_by_agent_id,
            channel_key=review_channel_key,
            message_type="status",
            content=self.relay_templates_service.render_markdown(request_payload),
            reply_to_message_id=None,
            source_message_id=job.source_message_id,
            created_at=now,
        )
        saved_review = await self.review_repository.update(
            ReviewRecord(
                **{
                    **asdict(review),
                    "request_message_id": request_message.id,
                    "updated_at": now,
                }
            )
        )
        await self._record_session_event(
            session_id=session.id,
            event_type="review.requested",
            actor_type="agent" if requested_by_agent_id is not None else "system",
            actor_id=requested_by_agent_id,
            payload={
                "review_id": saved_review.id,
                "job_id": job.id,
                "reviewer_agent_id": resolved_reviewer_id,
                "template_key": saved_review.template_key,
                "review_channel_key": review_channel_key,
                "request_message_id": request_message.id,
                "policy_metadata": policy_metadata,
            },
            created_at=now,
        )
        return ReviewStartResult(review=saved_review, request_message=request_message)

    async def submit_decision(
        self,
        *,
        review_id: str,
        decision: str,
        summary: str | None,
        required_changes: list[str] | None = None,
        notes: str | None = None,
        revision_priority: str = "normal",
        requested_by_agent_id: str | None = None,
        revision_instructions: str | None = None,
    ) -> ReviewDecisionResult:
        """Record a review decision and optionally create a revise job."""
        review = await self._get_review(review_id)
        if review.review_status != "requested":
            if review.review_status == decision:
                return await self._load_existing_decision_result(review, decision=decision)
            raise ValueError(f"Review {review.id} is not awaiting a decision")
        job = await self._get_job(review.source_job_id)
        session = await self._get_session(review.session_id)
        required_changes_list = required_changes or []
        if decision not in {"approved", "changes_requested"}:
            raise ValueError(f"Unsupported review decision: {decision}")

        decision_payload = self.relay_templates_service.build_reviewer_to_builder_revise(
            job_id=job.id,
            job_title=job.title,
            reviewer_agent_id=review.reviewer_agent_id,
            decision=decision,
            summary=summary,
            required_changes=required_changes_list,
            revision_priority=revision_priority,
            next_actions=required_changes_list,
            notes=notes,
        )
        now = _utc_now()
        revision_job: JobRecord | None = None
        if decision == "changes_requested":
            revision_instructions_text = (
                revision_instructions
                if revision_instructions is not None
                else self.relay_templates_service.render_markdown(decision_payload)
            )
            revision_job = await self.job_service.create_job_for_agent(
                session_id=job.session_id,
                agent_id=job.assigned_agent_id,
                title=f"Revise: {job.title}",
                instructions=revision_instructions_text,
                channel_key=review.review_channel_key,
                priority=revision_priority,
                source_message_id=review.request_message_id or job.source_message_id,
                parent_job_id=job.id,
            )
            await self.offline_queue_service.schedule_job(
                revision_job.id,
                input_type="review_revise",
                input_payload={
                    "review_id": review.id,
                    "source_job_id": job.id,
                    "decision": decision,
                    "required_changes": required_changes_list,
                    "notes": notes,
                },
                relay_reason="manual_relay",
            )

        decision_message = await self._publish_message(
            session=session,
            sender_type="agent",
            sender_id=review.reviewer_agent_id,
            channel_key=review.review_channel_key,
            message_type="artifact_notice",
            content=self.relay_templates_service.render_markdown(decision_payload),
            reply_to_message_id=review.request_message_id,
            source_message_id=review.request_message_id or job.source_message_id,
            created_at=now,
        )
        summary_artifact = await self.artifact_manager.create_structured_artifact(
            job=job,
            artifact_type="json",
            title=f"Review decision for {job.title}",
            content_text=json.dumps(decision_payload, sort_keys=True),
            file_name=f"{review.id}-decision.json",
            mime_type="application/json",
            metadata={
                "artifact_kind": "review_summary",
                "review_id": review.id,
                "source_job_id": job.id,
                "decision": decision,
                "reviewer_agent_id": review.reviewer_agent_id,
                "revision_job_id": revision_job.id if revision_job is not None else None,
            },
            source_message_id=decision_message.id,
            channel_key=review.review_channel_key,
            created_at=now,
        )
        saved_review = await self.review_repository.update(
            ReviewRecord(
                **{
                    **asdict(review),
                    "review_status": decision,
                    "decision_message_id": decision_message.id,
                    "summary_artifact_id": summary_artifact.id,
                    "revision_job_id": revision_job.id if revision_job is not None else None,
                    "decision_payload_json": json.dumps(decision_payload, sort_keys=True),
                    "decided_at": now,
                    "updated_at": now,
                }
            )
        )
        await self._record_session_event(
            session_id=session.id,
            event_type="review.decision.recorded",
            actor_type="agent",
            actor_id=requested_by_agent_id or review.reviewer_agent_id,
            payload={
                "review_id": saved_review.id,
                "job_id": job.id,
                "decision": decision,
                "revision_job_id": revision_job.id if revision_job is not None else None,
                "summary_artifact_id": summary_artifact.id,
                "decision_message_id": decision_message.id,
            },
            created_at=now,
        )
        return ReviewDecisionResult(
            review=saved_review,
            decision_message=decision_message,
            summary_artifact=summary_artifact,
            revision_job=revision_job,
        )

    async def _load_existing_decision_result(
        self,
        review: ReviewRecord,
        *,
        decision: str,
    ) -> ReviewDecisionResult:
        if review.decision_message_id is None or review.summary_artifact_id is None:
            raise RuntimeError(
                f"Review {review.id} was already resolved but missing persisted side effects"
            )
        decision_message = await self._get_message(review.decision_message_id)
        summary_artifact = await self._get_artifact(review.summary_artifact_id)
        revision_job = (
            await self._get_job(review.revision_job_id)
            if review.revision_job_id is not None
            else None
        )
        if decision == "changes_requested" and revision_job is None:
            raise RuntimeError(
                f"Review {review.id} was already resolved but missing revision job state"
            )
        return ReviewDecisionResult(
            review=review,
            decision_message=decision_message,
            summary_artifact=summary_artifact,
            revision_job=revision_job,
        )

    async def _publish_message(
        self,
        *,
        session: SessionRecord,
        sender_type: str,
        sender_id: str | None,
        channel_key: str,
        message_type: str,
        content: str,
        reply_to_message_id: str | None,
        source_message_id: str | None,
        created_at: str,
    ) -> MessageRecord:
        message = MessageRecord(
            id=f"msg_{uuid4().hex}",
            session_id=session.id,
            channel_key=channel_key,
            sender_type=sender_type,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            content_format="markdown",
            reply_to_message_id=reply_to_message_id,
            source_message_id=source_message_id,
            visibility="session",
            created_at=created_at,
            updated_at=created_at,
        )
        created = await self.message_repository.create(message)
        await self.session_repository.update(
            SessionRecord(
                id=session.id,
                title=session.title,
                goal=session.goal,
                status=session.status,
                lead_agent_id=session.lead_agent_id,
                active_phase_id=session.active_phase_id,
                loop_guard_status=session.loop_guard_status,
                loop_guard_reason=session.loop_guard_reason,
                last_message_at=created_at,
                template_key=session.template_key,
                created_at=session.created_at,
                updated_at=created_at,
            )
        )
        return created

    async def _record_session_event(
        self,
        *,
        session_id: str,
        event_type: str,
        actor_type: str | None,
        actor_id: str | None,
        payload: dict[str, object] | None,
        created_at: str,
    ) -> None:
        await record_session_event(
            self.session_event_repository,
            session_id=session_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
            created_at=created_at,
        )

    async def _resolve_reviewer_agent(
        self,
        *,
        session: SessionRecord,
        explicit_reviewer_agent_id: str | None,
    ) -> str:
        participants = await self.participant_repository.list_by_session(session.id)
        participant_ids = {participant.agent_id for participant in participants}
        reviewer_ids = [
            participant.agent_id
            for participant in participants
            if participant.role == "reviewer" and participant.participant_status == "joined"
        ]
        if explicit_reviewer_agent_id is not None:
            if (
                explicit_reviewer_agent_id not in participant_ids
                and explicit_reviewer_agent_id != session.lead_agent_id
            ):
                raise LookupError(
                    f"Reviewer agent {explicit_reviewer_agent_id} is not a participant "
                    f"of session {session.id}"
                )
            return explicit_reviewer_agent_id
        if reviewer_ids:
            return reviewer_ids[0]
        if session.lead_agent_id is not None:
            return session.lead_agent_id
        if participants:
            return participants[0].agent_id
        raise LookupError(f"No reviewer available for session {session.id}")

    async def _has_active_review(self, job_id: str) -> bool:
        for review in await self.review_repository.list_by_job(job_id):
            if review.review_status == "requested":
                return True
        return False

    async def _get_review(self, review_id: str) -> ReviewRecord:
        review = await self.review_repository.get(review_id)
        if review is None:
            raise LookupError(f"Review not found: {review_id}")
        return review

    async def _get_message(self, message_id: str) -> MessageRecord:
        message = await self.message_repository.get(message_id)
        if message is None:
            raise LookupError(f"Message not found: {message_id}")
        return message

    async def _get_artifact(self, artifact_id: str) -> ArtifactRecord:
        artifact = await self.artifact_repository.get(artifact_id)
        if artifact is None:
            raise LookupError(f"Artifact not found: {artifact_id}")
        return artifact

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session
