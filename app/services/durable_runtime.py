"""Durable runtime recovery and replay loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.services.outbound_webhooks import OutboundDeliverySweepResult, OutboundWebhookService
from app.services.recovery import RecoveryService, RecoverySummary

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class DurableRuntimeSweepResult:
    """Summary for a single durable runtime sweep."""

    recovery: RecoverySummary
    outbound: OutboundDeliverySweepResult | None
    completed_at: str


class DurableRuntimeSupervisor:
    """Run restart recovery on a background cadence for durable deployments."""

    def __init__(
        self,
        *,
        recovery_service: RecoveryService,
        outbound_webhook_service: OutboundWebhookService | None = None,
        recovery_enabled: bool,
        poll_interval_seconds: float,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        self.recovery_service = recovery_service
        self.outbound_webhook_service = outbound_webhook_service
        self.recovery_enabled = recovery_enabled
        self.outbound_enabled = outbound_webhook_service is not None
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.last_result: DurableRuntimeSweepResult | None = None

    @property
    def enabled(self) -> bool:
        """Backward-compatible view of recovery loop enablement."""
        return self.recovery_enabled

    def is_running(self) -> bool:
        """Return whether the periodic loop is active."""
        return self._task is not None and not self._task.done()

    async def run_once(
        self,
        *,
        include_recovery: bool | None = None,
    ) -> DurableRuntimeSweepResult:
        """Run one recovery and replay sweep."""
        should_run_recovery = (
            self.recovery_enabled if include_recovery is None else include_recovery
        )
        if should_run_recovery:
            recovery = await self.recovery_service.recover()
        else:
            recovery = RecoverySummary(
                recovered_threads=0,
                offline_runtimes=0,
                replayed_jobs=0,
            )
        outbound = None
        if self.outbound_webhook_service is not None:
            outbound = await self.outbound_webhook_service.dispatch_due_deliveries()
        result = DurableRuntimeSweepResult(
            recovery=recovery,
            outbound=outbound,
            completed_at=_utc_now(),
        )
        self.last_result = result
        return result

    async def start(self) -> None:
        """Start the periodic recovery loop if enabled."""
        if (not self.recovery_enabled and not self.outbound_enabled) or self.is_running():
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
        except (asyncio.CancelledError, asyncio.TimeoutError, TimeoutError):
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
                except (asyncio.TimeoutError, TimeoutError):
                    try:
                        await self.run_once()
                    except Exception:
                        logger.exception("durable runtime sweep failed")
        except asyncio.CancelledError:
            return
