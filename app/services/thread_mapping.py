"""Session to Codex thread mapping service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from app.services.runtime_service import RuntimeService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CodexThreadBridge(Protocol):
    """Bridge interface needed by the thread mapping service."""

    async def thread_start(self, params: dict[str, Any] | None = None) -> Any:
        """Start a new Codex thread."""

    async def thread_resume(self, params: dict[str, Any] | None = None) -> Any:
        """Resume an existing Codex thread."""


@dataclass(frozen=True, slots=True)
class ThreadMappingRecord:
    """In-memory session-agent to Codex thread mapping."""

    id: str
    session_id: str
    agent_id: str
    runtime_id: str | None
    codex_thread_id: str
    is_active: bool
    created_at: str
    updated_at: str


class ThreadMappingStore:
    """Simple in-memory mapping store."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ThreadMappingRecord] = {}

    def get(self, session_id: str, agent_id: str) -> ThreadMappingRecord | None:
        """Return a mapping for the session/agent pair."""
        return self._records.get((session_id, agent_id))

    def upsert(self, record: ThreadMappingRecord) -> ThreadMappingRecord:
        """Store or replace a mapping."""
        self._records[(record.session_id, record.agent_id)] = record
        return record

    def list_by_session(self, session_id: str) -> list[ThreadMappingRecord]:
        """Return all mappings for a session."""
        return [record for record in self._records.values() if record.session_id == session_id]

    def deactivate(self, session_id: str, agent_id: str) -> ThreadMappingRecord | None:
        """Mark a mapping inactive without removing it from memory."""
        record = self._records.get((session_id, agent_id))
        if record is None:
            return None
        updated = ThreadMappingRecord(
            id=record.id,
            session_id=record.session_id,
            agent_id=record.agent_id,
            runtime_id=record.runtime_id,
            codex_thread_id=record.codex_thread_id,
            is_active=False,
            created_at=record.created_at,
            updated_at=_utc_now(),
        )
        self._records[(session_id, agent_id)] = updated
        return updated

    def clear(self) -> None:
        """Remove all mappings from memory."""
        self._records.clear()


class ThreadMappingService:
    """Create or reuse Codex threads for a session-agent pair."""

    def __init__(
        self,
        runtime_service: RuntimeService,
        store: ThreadMappingStore | None = None,
    ) -> None:
        self.runtime_service = runtime_service
        self.store = store or ThreadMappingStore()

    async def get_or_create_thread(
        self,
        *,
        session_id: str,
        agent_id: str,
        bridge: CodexThreadBridge,
    ) -> tuple[ThreadMappingRecord, bool]:
        """Return a thread mapping, creating or resuming as needed."""
        existing = self.store.get(session_id, agent_id)
        if existing is not None and existing.is_active:
            await bridge.thread_resume(
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "thread_id": existing.codex_thread_id,
                }
            )
            refreshed = ThreadMappingRecord(
                id=existing.id,
                session_id=existing.session_id,
                agent_id=existing.agent_id,
                runtime_id=existing.runtime_id,
                codex_thread_id=existing.codex_thread_id,
                is_active=True,
                created_at=existing.created_at,
                updated_at=_utc_now(),
            )
            return self.store.upsert(refreshed), False

        runtime = await self.runtime_service.get_latest_runtime_for_agent(agent_id)
        response = await bridge.thread_start(
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "runtime_id": runtime.id if runtime is not None else None,
            }
        )
        thread_id = self._extract_thread_id(response)
        created_at = _utc_now()
        record = ThreadMappingRecord(
            id=f"ctm_{uuid4().hex}",
            session_id=session_id,
            agent_id=agent_id,
            runtime_id=runtime.id if runtime is not None else None,
            codex_thread_id=thread_id,
            is_active=True,
            created_at=created_at,
            updated_at=created_at,
        )
        return self.store.upsert(record), True

    async def deactivate_thread(
        self,
        session_id: str,
        agent_id: str,
    ) -> ThreadMappingRecord | None:
        """Mark a mapping inactive in memory."""
        return self.store.deactivate(session_id, agent_id)

    @staticmethod
    def _extract_thread_id(response: Any) -> str:
        """Extract a Codex thread id from a bridge response."""
        if isinstance(response, dict) and "result" in response:
            result = response["result"]
        else:
            result = getattr(response, "result", response)
        if isinstance(result, dict):
            thread = result.get("thread")
            if isinstance(thread, dict):
                thread_id = thread.get("id") or thread.get("thread_id")
                if thread_id is not None:
                    return str(thread_id)
            thread_id = (
                result.get("thread_id")
                or result.get("threadId")
                or result.get("codex_thread_id")
            )
            if thread_id is not None:
                return str(thread_id)
        raise ValueError("Bridge response did not include a thread id")
