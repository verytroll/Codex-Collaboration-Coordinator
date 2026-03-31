"""Process manager for the Codex app-server subprocess."""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path


class CodexProcessManager:
    """Start and stop a local `codex app-server` process."""

    def __init__(
        self,
        command: Sequence[str] | str | None = None,
        *,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        startup_timeout_seconds: float = 10.0,
    ) -> None:
        self.command = self._normalize_command(command)
        self.cwd = Path(cwd) if cwd is not None else None
        self.env = dict(env) if env is not None else None
        self.startup_timeout_seconds = startup_timeout_seconds
        self.process: subprocess.Popen[bytes] | None = None
        self.stderr_lines: list[str] = []
        self._stderr_thread: threading.Thread | None = None

    @staticmethod
    def _normalize_command(command: Sequence[str] | str | None) -> list[str]:
        """Normalize a command definition into a subprocess argument list."""
        if command is None:
            resolved = shutil.which("codex")
            if resolved is not None:
                return [resolved, "app-server"]
            if os.name == "nt":
                return ["codex", "app-server"]
            return ["codex", "app-server"]
        if isinstance(command, str):
            return shlex.split(command)
        return list(command)

    def is_running(self) -> bool:
        """Return whether the process is currently alive."""
        return self.process is not None and self.process.poll() is None

    async def start(self) -> subprocess.Popen[bytes]:
        """Start the Codex app-server subprocess if needed."""
        if self.is_running():
            return self.process  # type: ignore[return-value]

        self.process = await asyncio.to_thread(self._start_sync)
        return self.process

    async def stop(self) -> None:
        """Stop the Codex app-server subprocess if it is running."""
        process = self.process
        if process is None:
            return

        if process.poll() is None:
            await asyncio.to_thread(process.terminate)
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(process.wait),
                    timeout=self.startup_timeout_seconds,
                )
            except TimeoutError:
                await asyncio.to_thread(process.kill)
                await asyncio.to_thread(process.wait)

        await self._join_stderr_thread()
        self.process = None

    def _start_sync(self) -> subprocess.Popen[bytes]:
        """Start the subprocess in a worker thread."""
        process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd) if self.cwd is not None else None,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr_sync,
            args=(process,),
            name="codex-bridge-stderr",
            daemon=True,
        )
        self._stderr_thread.start()
        return process

    def _drain_stderr_sync(self, process: subprocess.Popen[bytes]) -> None:
        """Collect stderr lines so the subprocess cannot block on output."""
        if process.stderr is None:
            return

        while True:
            line = process.stderr.readline()
            if line == b"":
                return
            self.stderr_lines.append(line.decode("utf-8", errors="replace").rstrip())

    async def _join_stderr_thread(self) -> None:
        """Wait for the stderr drainer thread to finish."""
        thread = self._stderr_thread
        if thread is None:
            return

        await asyncio.to_thread(thread.join, self.startup_timeout_seconds)
        self._stderr_thread = None
