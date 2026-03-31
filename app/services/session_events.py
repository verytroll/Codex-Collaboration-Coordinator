"""Session event logging helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.session_events import SessionEventRecord, SessionEventRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def record_session_event(
    event_repository: SessionEventRepository,
    *,
    session_id: str,
    event_type: str,
    actor_type: str | None = None,
    actor_id: str | None = None,
    payload: dict[str, object] | None = None,
    created_at: str | None = None,
) -> SessionEventRecord:
    """Store a session event in the event log."""

    event = SessionEventRecord(
        id=f"evt_{uuid4().hex}",
        session_id=session_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        event_payload_json=json.dumps(payload, sort_keys=True) if payload is not None else None,
        created_at=created_at or _utc_now(),
    )
    return await event_repository.create(event)
