"""Deterministic mock Codex bridge for tests and local replay checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class MockCodexBridgeClient:
    """Minimal Codex bridge implementation that never starts a subprocess."""

    _client_info: dict[str, Any] | None = None

    async def initialize(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"ok": True, "result": {"initialized": True, "params": dict(params or {})}}

    async def thread_start(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        thread_id = payload.get("thread_id") or f"thr_mock_{uuid4().hex}"
        return {"ok": True, "result": {"thread": {"id": thread_id}, "thread_id": thread_id}}

    async def thread_resume(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        thread_id = payload.get("thread_id") or f"thr_mock_{uuid4().hex}"
        return {"ok": True, "result": {"thread": {"id": thread_id}, "resumed": True}}

    async def turn_start(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        turn_id = f"turn_mock_{uuid4().hex}"
        return {
            "ok": True,
            "result": {
                "turn_id": turn_id,
                "status": "running",
                "output_text": "Mock bridge accepted the turn.",
            },
        }

    async def turn_steer(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        turn_id = f"turn_mock_{uuid4().hex}"
        return {"ok": True, "result": {"turn_id": turn_id, "steered": True}}

    async def turn_interrupt(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        return {
            "ok": True,
            "result": {"turn_id": payload.get("turn_id"), "interrupted": True},
        }

    async def thread_compact_start(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        return {
            "ok": True,
            "result": {"thread_id": payload.get("thread_id"), "compacted": True},
        }

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        return {"ok": True, "result": {"method": method, "params": dict(params or {})}}

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        return None

    async def notifications(self) -> list[dict[str, Any]]:
        return []

    async def aclose(self) -> None:
        return None
