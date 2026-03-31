from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from textwrap import dedent

from app.codex_bridge import CodexProcessManager, JsonRpcClient


def _write_mock_server(script_path: Path) -> None:
    script_path.write_text(
        dedent(
            """
from __future__ import annotations

import json
import sys


def main() -> int:
    for raw_line in sys.stdin:
        payload = json.loads(raw_line)
        method = payload["method"]
        request_id = payload.get("id")

        if method == "initialize":
            result = {"status": "ready", "transport": "stdio"}
        elif method == "thread/start":
            result = {"thread_id": "thr_123", "started": True}
        elif method == "thread/resume":
            result = {"thread_id": "thr_123", "resumed": True}
        elif method == "turn/start":
            result = {"turn_id": "turn_123", "started": True}
        elif method == "turn/steer":
            result = {"turn_id": "turn_123", "steered": True}
        elif method == "turn/interrupt":
            result = {"turn_id": "turn_123", "interrupted": True}
        elif method == "thread/compact/start":
            result = {"thread_id": "thr_123", "compacted": True}
        else:
            result = {"echo": payload.get("params")}

        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        sys.stdout.write(json.dumps(response) + "\\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


async def _exercise_bridge(script_path: Path) -> None:
    manager = CodexProcessManager(command=[sys.executable, "-u", str(script_path)])
    process = await manager.start()
    client = JsonRpcClient(process)

    try:
        initialize_response = await client.initialize()
        assert initialize_response.ok
        assert initialize_response.result == {"status": "ready", "transport": "stdio"}

        thread_start_response = await client.thread_start({"session_id": "session_1"})
        assert thread_start_response.result["thread_id"] == "thr_123"

        thread_resume_response = await client.thread_resume({"thread_id": "thr_123"})
        assert thread_resume_response.result["resumed"] is True

        turn_start_response = await client.turn_start({"thread_id": "thr_123", "message": "hello"})
        assert turn_start_response.result["turn_id"] == "turn_123"

        turn_steer_response = await client.turn_steer(
            {"turn_id": "turn_123", "message": "keep going"}
        )
        assert turn_steer_response.result["steered"] is True

        turn_interrupt_response = await client.turn_interrupt({"turn_id": "turn_123"})
        assert turn_interrupt_response.result["interrupted"] is True

        thread_compact_response = await client.thread_compact_start({"thread_id": "thr_123"})
        assert thread_compact_response.result["compacted"] is True
    finally:
        await client.aclose()
        await manager.stop()


def test_codex_bridge_smoke(tmp_path) -> None:
    script_path = tmp_path / "mock_codex_app_server.py"
    _write_mock_server(script_path)

    asyncio.run(_exercise_bridge(script_path))
