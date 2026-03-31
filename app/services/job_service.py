"""Job creation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import MessageRecord
from app.services.mention_router import ResolvedMention
from app.services.runtime_service import RuntimeService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JobService:
    """Create jobs from routed mentions."""

    def __init__(
        self,
        job_repository: JobRepository,
        runtime_service: RuntimeService,
    ) -> None:
        self.job_repository = job_repository
        self.runtime_service = runtime_service

    async def create_jobs_for_mentions(
        self,
        *,
        message: MessageRecord,
        mentions: list[ResolvedMention],
    ) -> list[JobRecord]:
        """Create at most one job per mentioned agent."""
        created_jobs: list[JobRecord] = []
        seen_agents: set[str] = set()
        for mention in mentions:
            if mention.mentioned_agent_id in seen_agents:
                continue
            created_jobs.append(
                await self.create_job_for_mention(
                    message=message,
                    mention=mention,
                )
            )
            seen_agents.add(mention.mentioned_agent_id)
        return created_jobs

    async def create_job_for_agent(
        self,
        *,
        session_id: str,
        agent_id: str,
        title: str,
        instructions: str | None,
        source_message_id: str | None = None,
        parent_job_id: str | None = None,
        runtime_id: str | None = None,
    ) -> JobRecord:
        """Create a single queued job for a specific agent."""
        resolved_runtime_id = runtime_id
        if resolved_runtime_id is None:
            latest_runtime = await self.runtime_service.get_latest_runtime_for_agent(agent_id)
            resolved_runtime_id = latest_runtime.id if latest_runtime is not None else None

        now = _utc_now()
        job = JobRecord(
            id=f"job_{uuid4().hex}",
            session_id=session_id,
            assigned_agent_id=agent_id,
            runtime_id=resolved_runtime_id,
            source_message_id=source_message_id,
            parent_job_id=parent_job_id,
            title=title[:120] if title else "Untitled job",
            instructions=instructions,
            status="queued",
            hop_count=0,
            priority="normal",
            codex_runtime_id=None,
            codex_thread_id=None,
            active_turn_id=None,
            last_known_turn_status=None,
            result_summary=None,
            error_code=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        return await self.job_repository.create(job)

    async def create_job_for_mention(
        self,
        *,
        message: MessageRecord,
        mention: ResolvedMention,
    ) -> JobRecord:
        """Create a single queued job for a mention."""
        return await self.create_job_for_agent(
            session_id=message.session_id,
            agent_id=mention.mentioned_agent_id,
            title=self._build_title(message.content, mention.mention_text),
            instructions=message.content,
            source_message_id=message.id,
            runtime_id=await self._resolve_runtime_id(mention),
        )

    async def _resolve_runtime_id(self, mention: ResolvedMention) -> str | None:
        """Resolve the runtime id for a mention."""
        if mention.runtime_id is not None:
            return mention.runtime_id
        runtime = await self.runtime_service.get_latest_runtime_for_agent(
            mention.mentioned_agent_id
        )
        if runtime is None:
            return None
        return runtime.id

    @staticmethod
    def _build_title(content: str, mention_text: str) -> str:
        """Build a short job title from the source message."""
        normalized_content = " ".join(content.split())
        if not normalized_content:
            return mention_text
        return normalized_content[:120]
