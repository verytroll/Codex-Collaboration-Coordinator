"""Async JSON-RPC client for the Codex app-server subprocess."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from itertools import count
from typing import Any

from app.codex_bridge.models import JsonRpcRequest, JsonRpcResponse


class JsonRpcClient:
    """Line-delimited JSON-RPC client on top of a subprocess pipe."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        *,
        default_timeout_seconds: float = 30.0,
    ) -> None:
        self.process = process
        self.default_timeout_seconds = default_timeout_seconds
        self._request_ids = count(1)
        self._pending: dict[int | str, asyncio.Future[JsonRpcResponse]] = {}
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader_task: asyncio.Task[None] | None = None
        self._write_lock = asyncio.Lock()
        self._closed = False

    async def initialize(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `initialize` primitive."""
        return await self.call("initialize", params)

    async def thread_start(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `thread/start` primitive."""
        return await self.call("thread/start", params)

    async def thread_resume(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `thread/resume` primitive."""
        return await self.call("thread/resume", params)

    async def turn_start(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `turn/start` primitive."""
        return await self.call("turn/start", params)

    async def turn_steer(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `turn/steer` primitive."""
        return await self.call("turn/steer", params)

    async def turn_interrupt(self, params: Mapping[str, Any] | None = None) -> JsonRpcResponse:
        """Call the `turn/interrupt` primitive."""
        return await self.call("turn/interrupt", params)

    async def thread_compact_start(
        self,
        params: Mapping[str, Any] | None = None,
    ) -> JsonRpcResponse:
        """Call the `thread/compact/start` primitive."""
        return await self.call("thread/compact/start", params)

    async def call(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> JsonRpcResponse:
        """Send a JSON-RPC request and wait for the matching response."""
        self._ensure_reader_task()
        if self.process.stdin is None:
            raise RuntimeError("JSON-RPC process stdin is not available")

        request_id = next(self._request_ids)
        request = JsonRpcRequest(
            method=method,
            params=dict(params) if params is not None else None,
            request_id=request_id,
        )
        response_future: asyncio.Future[JsonRpcResponse] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[request_id] = response_future

        try:
            await self._send_request(request)
            return await asyncio.wait_for(
                response_future,
                timeout_seconds or self.default_timeout_seconds,
            )
        except Exception:
            self._pending.pop(request_id, None)
            raise

    async def notifications(self) -> list[dict[str, Any]]:
        """Drain queued notifications emitted by the server."""
        notifications: list[dict[str, Any]] = []
        while not self._notifications.empty():
            notifications.append(await self._notifications.get())
        return notifications

    async def aclose(self) -> None:
        """Close the client and cancel its background reader."""
        self._closed = True
        await self._cancel_reader_task()

    async def _send_request(self, request: JsonRpcRequest) -> None:
        """Write a JSON-RPC request to the subprocess stdin."""
        raw_payload = json.dumps(request.to_dict(), separators=(",", ":")) + "\n"
        async with self._write_lock:
            self.process.stdin.write(raw_payload.encode("utf-8"))
            await self.process.stdin.drain()

    def _ensure_reader_task(self) -> None:
        """Start the response reader task if necessary."""
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self) -> None:
        """Read JSON-RPC responses and notifications from stdout."""
        if self.process.stdout is None:
            raise RuntimeError("JSON-RPC process stdout is not available")

        try:
            while True:
                raw_line = await self.process.stdout.readline()
                if raw_line == b"":
                    break

                payload = json.loads(raw_line.decode("utf-8"))
                if not isinstance(payload, dict):
                    continue

                if "id" in payload and ("result" in payload or "error" in payload):
                    await self._resolve_response(JsonRpcResponse.from_dict(payload))
                else:
                    await self._notifications.put(payload)
        except Exception as exc:
            self._fail_pending(exc)
            if not self._closed:
                raise
        else:
            self._fail_pending(ConnectionError("Codex bridge process closed stdout"))

    async def _resolve_response(self, response: JsonRpcResponse) -> None:
        """Resolve a pending request future."""
        future = self._pending.pop(response.request_id, None)
        if future is None:
            await self._notifications.put(response.to_dict())
            return

        if future.done():
            return
        future.set_result(response)

    def _fail_pending(self, exc: BaseException) -> None:
        """Fail all pending request futures with the given exception."""
        pending = list(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(exc)

    async def _cancel_reader_task(self) -> None:
        """Cancel the reader task if it exists."""
        task = self._reader_task
        if task is None:
            return

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._reader_task = None
