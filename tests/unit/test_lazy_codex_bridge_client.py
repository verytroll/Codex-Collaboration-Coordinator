from __future__ import annotations

import asyncio

import app.codex_bridge.lazy_client as lazy_client_module
from app.codex_bridge import LazyCodexBridgeClient
from app.codex_bridge.models import JsonRpcResponse
from app.core.version import APP_VERSION


class FakeProcessManager:
    def __init__(self) -> None:
        self.start_calls = 0
        self.stop_calls = 0

    async def start(self) -> object:
        self.start_calls += 1
        return object()

    async def stop(self) -> None:
        self.stop_calls += 1


class FakeJsonRpcClient:
    def __init__(self, process: object) -> None:
        self.process = process
        self.initialize_calls: list[dict[str, object] | None] = []
        self.thread_start_calls: list[dict[str, object] | None] = []
        self.closed = False

    async def initialize(self, params=None) -> JsonRpcResponse:
        self.initialize_calls.append(params)
        return JsonRpcResponse(
            request_id=1,
            result={"status": "ready", "transport": "stdio"},
        )

    async def thread_start(self, params=None) -> JsonRpcResponse:
        self.thread_start_calls.append(params)
        return JsonRpcResponse(request_id=2, result={"thread_id": "thr_1"})

    async def aclose(self) -> None:
        self.closed = True


def test_lazy_codex_bridge_client_defers_process_start(monkeypatch) -> None:
    manager = FakeProcessManager()
    monkeypatch.setattr(lazy_client_module, "JsonRpcClient", FakeJsonRpcClient)
    bridge = LazyCodexBridgeClient(manager)

    async def exercise() -> None:
        response = await bridge.thread_start({"session_id": "ses_1"})
        assert response.result == {"thread_id": "thr_1"}
        assert manager.start_calls == 1
        assert bridge._client is not None
        assert bridge._client.initialize_calls == [
            {
                "transport": "stdio",
                "clientInfo": {
                    "name": "codex-collaboration-coordinator",
                    "version": APP_VERSION,
                },
            }
        ]
        assert bridge._client.thread_start_calls == [{"session_id": "ses_1"}]

        await bridge.thread_start({"session_id": "ses_2"})
        assert manager.start_calls == 1
        assert bridge._client.initialize_calls == [
            {
                "transport": "stdio",
                "clientInfo": {
                    "name": "codex-collaboration-coordinator",
                    "version": APP_VERSION,
                },
            }
        ]
        assert bridge._client.thread_start_calls == [
            {"session_id": "ses_1"},
            {"session_id": "ses_2"},
        ]

        await bridge.aclose()
        assert manager.stop_calls == 1
        assert bridge._client is None

    asyncio.run(exercise())
