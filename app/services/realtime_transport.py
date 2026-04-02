"""Helpers for SSE-based realtime transport."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from time import monotonic
from typing import TypeVar

T = TypeVar("T")


def resolve_resume_sequence(since_sequence: int | None, last_event_id: str | None) -> int:
    """Resolve a replay cursor from query and EventSource reconnect metadata."""
    cursor = since_sequence or 0
    if last_event_id is None or not last_event_id.strip():
        return max(cursor, 0)
    try:
        last_sequence = int(last_event_id)
    except ValueError:
        return max(cursor, 0)
    return max(cursor, last_sequence, 0)


def format_sse_frame(
    event: str,
    data: object,
    *,
    event_id: int | str | None = None,
    retry_ms: int | None = None,
) -> str:
    """Format a single SSE frame."""
    lines: list[str] = []
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, sort_keys=True)}")
    return "\n".join(lines) + "\n\n"


def format_heartbeat(comment: str = "keepalive") -> str:
    """Format a heartbeat comment frame."""
    return f": {comment}\n\n"


async def stream_polling_sse(
    *,
    initial_sequence: int,
    poll_once: Callable[[int], Awaitable[tuple[T, int]]],
    event_name: str,
    request_is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    emit_initial: bool = True,
    retry_ms: int = 3000,
    poll_interval_seconds: float = 2.0,
    max_idle_seconds: float = 2.0,
) -> AsyncIterator[str]:
    """Poll a replayable snapshot and expose it over SSE."""
    cursor = initial_sequence
    emitted_initial = False
    last_heartbeat_at = monotonic()
    while True:
        if request_is_disconnected is not None and await request_is_disconnected():
            return
        payload, next_cursor = await poll_once(cursor)
        should_emit = (emit_initial and not emitted_initial) or next_cursor > cursor
        if should_emit:
            yield format_sse_frame(
                event_name,
                payload,
                event_id=next_cursor,
                retry_ms=retry_ms,
            )
            emitted_initial = True
            cursor = next_cursor
            last_heartbeat_at = monotonic()
        elif monotonic() - last_heartbeat_at >= max_idle_seconds:
            return
        await asyncio.sleep(poll_interval_seconds)
