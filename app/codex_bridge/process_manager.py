"""Process manager for the Codex app-server subprocess."""

from __future__ import annotations

import asyncio
import shlex
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
        self.process: asyncio.subprocess.Process | None = None
        self.stderr_lines: list[str] = []
        self._stderr_task: asyncio.Task[None] | None = None

    @staticmethod
    def _normalize_command(command: Sequence[str] | str | None) -> list[str]:
        """Normalize a command definition into a subprocess argument list."""
        if command is None:
            return ["codex", "app-server"]
        if isinstance(command, str):
            return shlex.split(command)
        return list(command)

    def is_running(self) -> bool:
        """Return whether the process is currently alive."""
        return self.process is not None and self.process.returncode is None

    async def start(self) -> asyncio.subprocess.Process:
        """Start the Codex app-server subprocess if needed."""
        if self.is_running():
            return self.process  # type: ignore[return-value]

        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=str(self.cwd) if self.cwd is not None else None,
            env=self.env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr())
        return self.process

    async def stop(self) -> None:
        """Stop the Codex app-server subprocess if it is running."""
        process = self.process
        if process is None:
            return

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=self.startup_timeout_seconds)
            except TimeoutError:
                process.kill()
                await process.wait()

        await self._cancel_stderr_task()
        self.process = None

    async def _drain_stderr(self) -> None:
        """Collect stderr lines so the subprocess cannot block on output."""
        process = self.process
        if process is None or process.stderr is None:
            return

        while True:
            line = await process.stderr.readline()
            if line == b"":
                return
            self.stderr_lines.append(line.decode("utf-8", errors="replace").rstrip())

    async def _cancel_stderr_task(self) -> None:
        """Cancel the stderr drainer if it exists."""
        task = self._stderr_task
        if task is None:
            return

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._stderr_task = None
