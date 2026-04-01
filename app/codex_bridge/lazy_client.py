"""Lazy Codex bridge client that starts the subprocess on demand."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.codex_bridge.jsonrpc_client import JsonRpcClient
from app.codex_bridge.models import JsonRpcResponse
from app.codex_bridge.process_manager import CodexProcessManager
from app.core.logging import get_logger
from app.core.telemetry import get_telemetry_service

logger = get_logger(__name__)


class LazyCodexBridgeClient:
    """Proxy a Codex bridge process and initialize it only when needed."""

    _default_client_info = {
        "name": "codex-collaboration-coordinator",
        "version": "0.1.0",
    }

    def __init__(self, process_manager: CodexProcessManager) -> None:
        self.process_manager = process_manager
        self._client: JsonRpcClient | None = None
        self._initialized_response: JsonRpcResponse | None = None

    async def initialize(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Start the subprocess and send the initialize request on demand."""
        if self._initialized_response is not None:
            return self._initialized_response
        client = await self._ensure_client()
        self._initialized_response = await client.initialize(self._build_initialize_params(params))
        try:
            self._raise_for_error(self._initialized_response)
        except Exception:
            await get_telemetry_service().record_sample(
                "codex_bridge",
                status="error",
                metrics={
                    "event": "initialize",
                    "response": self._initialized_response.model_dump(mode="json"),
                },
            )
            raise
        logger.info("codex bridge initialized")
        await get_telemetry_service().record_sample(
            "codex_bridge",
            metrics={
                "event": "initialize",
                "response": self._initialized_response.model_dump(mode="json"),
            },
        )
        return self._initialized_response

    async def thread_start(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `thread/start` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.thread_start(params)

    async def thread_resume(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `thread/resume` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.thread_resume(params)

    async def turn_start(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `turn/start` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.turn_start(params)

    async def turn_steer(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `turn/steer` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.turn_steer(params)

    async def turn_interrupt(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `turn/interrupt` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.turn_interrupt(params)

    async def thread_compact_start(self, params: Mapping[str, Any] | None = None) -> Any:
        """Call `thread/compact/start` after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.thread_compact_start(params)

    async def call(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Forward an arbitrary JSON-RPC call after lazy initialization."""
        client = await self._ensure_initialized()
        return await client.call(method, params, timeout_seconds=timeout_seconds)

    async def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        """Forward a JSON-RPC notification after lazy initialization."""
        client = await self._ensure_initialized()
        await client.notify(method, params)

    async def notifications(self) -> list[dict[str, Any]]:
        """Drain queued notifications if the bridge has been started."""
        client = self._client
        if client is None:
            return []
        return await client.notifications()

    async def aclose(self) -> None:
        """Close the underlying client and process manager."""
        client = self._client
        self._client = None
        self._initialized_response = None
        await self.process_manager.stop()
        if client is not None:
            await client.aclose()

    async def _ensure_client(self) -> JsonRpcClient:
        """Create the underlying JSON-RPC client if needed."""
        if self._client is not None:
            return self._client

        process = await self.process_manager.start()
        self._client = JsonRpcClient(process)
        return self._client

    async def _ensure_initialized(self) -> JsonRpcClient:
        """Ensure the bridge has been initialized before use."""
        if self._initialized_response is not None:
            return await self._ensure_client()

        client = await self._ensure_client()
        try:
            self._initialized_response = await client.initialize(self._build_initialize_params())
            self._raise_for_error(self._initialized_response)
        except Exception:
            await get_telemetry_service().record_sample(
                "codex_bridge",
                status="error",
                metrics={"event": "initialize"},
            )
            await self.aclose()
            raise
        return client

    def _build_initialize_params(
        self,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the initialize payload expected by Codex app-server."""
        payload = dict(params) if params is not None else {}
        payload.setdefault("transport", "stdio")
        payload.setdefault("clientInfo", dict(self._default_client_info))
        return payload

    @staticmethod
    def _raise_for_error(response: JsonRpcResponse) -> None:
        """Surface initialize errors as exceptions."""
        if response.ok:
            return
        message = response.error.message if response.error is not None else "initialize failed"
        raise RuntimeError(message)
