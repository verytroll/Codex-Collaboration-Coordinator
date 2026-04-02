"""Durable runtime recovery and replay loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.services.recovery import RecoveryService, RecoverySummary

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class DurableRuntimeSweepResult:
    """Summary for a single durable runtime sweep."""

    recovery: RecoverySummary
    completed_at: str


class DurableRuntimeSupervisor:
    """Run restart recovery on a background cadence for durable deployments."""

    def __init__(
        self,
        *,
        recovery_service: RecoveryService,
        enabled: bool,
        poll_interval_seconds: float,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        self.recovery_service = recovery_service
        self.enabled = enabled
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.last_result: DurableRuntimeSweepResult | None = None

    def is_running(self) -> bool:
        """Return whether the periodic loop is active."""
        return self._task is not None and not self._task.done()

    async def run_once(self) -> DurableRuntimeSweepResult:
        """Run one recovery and replay sweep."""
        recovery = await self.recovery_service.recover()
        result = DurableRuntimeSweepResult(
            recovery=recovery,
            completed_at=_utc_now(),
        )
        self.last_result = result
        return result

    async def start(self) -> None:
        """Start the periodic recovery loop if enabled."""
        if not self.enabled or self.is_running():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="durable-runtime-supervisor")

    async def stop(self) -> None:
        """Stop the periodic recovery loop."""
        task = self._task
        if task is None:
            return
        self._stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run_loop(self) -> None:
        """Repeat recovery sweeps on a fixed cadence."""
        try:
            while True:
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self.poll_interval_seconds
                    )
                    return
                except TimeoutError:
                    try:
                        await self.run_once()
                    except Exception:
                        logger.exception("durable runtime sweep failed")
        except asyncio.CancelledError:
            return
