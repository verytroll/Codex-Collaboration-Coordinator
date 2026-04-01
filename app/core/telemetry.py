"""In-memory telemetry collection for live/recent observability."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.logging import get_log_context


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


@dataclass(frozen=True, slots=True)
class TelemetrySampleRecord:
    """A single time-stamped telemetry sample."""

    kind: str
    generated_at: str
    status: str
    correlation: dict[str, str]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Serialize the sample into a JSON-friendly dictionary."""
        return {
            "kind": self.kind,
            "generated_at": self.generated_at,
            "status": self.status,
            "correlation": self.correlation,
            "metrics": self.metrics,
        }


class CoordinatorTelemetryService:
    """Collect a small in-memory telemetry timeline for the current process."""

    def __init__(self, *, max_samples: int = 200) -> None:
        self.max_samples = max_samples
        self._samples: deque[TelemetrySampleRecord] = deque(maxlen=max_samples)
        self._lock = Lock()

    async def record_sample(
        self,
        kind: str,
        *,
        metrics: dict[str, Any],
        status: str = "ok",
        correlation: dict[str, str] | None = None,
    ) -> TelemetrySampleRecord:
        """Store a new telemetry sample and return it."""
        sample = TelemetrySampleRecord(
            kind=kind,
            generated_at=_utc_now(),
            status=status,
            correlation=self._merge_correlation(correlation),
            metrics=dict(metrics),
        )
        with self._lock:
            self._samples.append(sample)
        return sample

    async def get_surface(self) -> dict[str, Any]:
        """Return the recent telemetry timeline and derived summary."""
        with self._lock:
            samples = list(self._samples)
        latest_by_kind = self._latest_by_kind(samples)
        summary = self._build_summary(samples, latest_by_kind)
        return {
            "generated_at": _utc_now(),
            "window_size": self.max_samples,
            "sample_counts": dict(Counter(sample.kind for sample in samples)),
            "summary": summary,
            "latest": {kind: sample.as_dict() for kind, sample in latest_by_kind.items()},
            "recent_samples": [sample.as_dict() for sample in samples[-20:]],
        }

    def _build_summary(
        self,
        samples: list[TelemetrySampleRecord],
        latest_by_kind: dict[str, TelemetrySampleRecord],
    ) -> dict[str, Any]:
        latest_metrics = self._latest_metrics(
            latest_by_kind,
            ("operator_dashboard", "system_status", "debug_surface"),
        )
        runtime_metrics = self._latest_metrics(
            latest_by_kind,
            ("runtime_pool_diagnostics", "runtime_assignment"),
        )
        public_metrics = self._latest_metrics(
            latest_by_kind,
            ("operator_dashboard", "public_event_stream", "public_task_projection"),
        )
        bridge_samples = [sample for sample in samples if sample.kind == "codex_bridge"]
        bridge_error_count = sum(1 for sample in bridge_samples if sample.status != "ok")
        bridge_total = len(bridge_samples)
        return {
            "queue_depth": int(self._number_from_metrics(latest_metrics, "queue_depth", 0)),
            "average_job_latency_seconds": self._maybe_float_from_metrics(
                latest_metrics,
                "average_job_latency_seconds",
            ),
            "average_phase_duration_seconds": self._maybe_float_from_metrics(
                latest_metrics,
                "average_phase_duration_seconds",
            ),
            "pending_review_bottlenecks": int(
                self._number_from_metrics(latest_metrics, "pending_review_bottlenecks", 0)
            ),
            "degraded_runtime_pools": self._degraded_runtime_pools(latest_metrics),
            "runtime_pool_pressure": _coerce_mapping(latest_metrics.get("runtime_pool_pressure"))
            if isinstance(latest_metrics, dict)
            else {},
            "runtime_pool_summary": _coerce_mapping(runtime_metrics.get("summary"))
            if isinstance(runtime_metrics, dict)
            else {},
            "public_task_throughput": _coerce_mapping(public_metrics.get("public_task_throughput"))
            if isinstance(public_metrics, dict)
            else {},
            "bridge": {
                "total_samples": bridge_total,
                "error_samples": bridge_error_count,
                "error_rate": (bridge_error_count / bridge_total if bridge_total > 0 else 0.0),
            },
        }

    def _latest_by_kind(
        self,
        samples: list[TelemetrySampleRecord],
    ) -> dict[str, TelemetrySampleRecord]:
        latest: dict[str, TelemetrySampleRecord] = {}
        for sample in samples:
            latest[sample.kind] = sample
        return latest

    def _latest_metrics(
        self,
        latest_by_kind: dict[str, TelemetrySampleRecord],
        kinds: tuple[str, ...],
    ) -> dict[str, Any]:
        for kind in kinds:
            sample = latest_by_kind.get(kind)
            if sample is not None:
                return sample.metrics
        return {}

    def _degraded_runtime_pools(self, metrics: dict[str, Any]) -> list[str]:
        degraded = metrics.get("degraded_runtime_pools")
        if isinstance(degraded, list):
            return [item for item in degraded if isinstance(item, str)]
        runtime_pools = metrics.get("runtime_pools")
        if not isinstance(runtime_pools, list):
            return []
        degraded_pools: list[str] = []
        for pool in runtime_pools:
            if not isinstance(pool, dict):
                continue
            if pool.get("pool_status") == "ready":
                continue
            pool_key = pool.get("pool_key")
            if isinstance(pool_key, str):
                degraded_pools.append(pool_key)
        return degraded_pools

    @staticmethod
    def _number_from_metrics(
        metrics: dict[str, Any], key: str, default: int | float
    ) -> int | float:
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return value
        return default

    @staticmethod
    def _maybe_float_from_metrics(metrics: dict[str, Any], key: str) -> float | None:
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _merge_correlation(correlation: dict[str, str] | None) -> dict[str, str]:
        merged = {key: value for key, value in get_log_context().items() if value != "-"}
        if correlation is not None:
            merged.update(
                {key: value for key, value in correlation.items() if value and value != "-"}
            )
        return merged


_TELEMETRY_SERVICE = CoordinatorTelemetryService()


def get_telemetry_service() -> CoordinatorTelemetryService:
    """Return the shared in-memory telemetry service."""
    return _TELEMETRY_SERVICE
