"""Factories for Codex bridge clients."""

from __future__ import annotations

from app.codex_bridge.lazy_client import LazyCodexBridgeClient
from app.codex_bridge.mock_client import MockCodexBridgeClient
from app.codex_bridge.process_manager import CodexProcessManager


def create_codex_bridge_client(mode: str) -> LazyCodexBridgeClient | MockCodexBridgeClient:
    """Create the Codex bridge client for the requested mode."""
    normalized = mode.strip().lower()
    if normalized == "mock":
        return MockCodexBridgeClient()
    return LazyCodexBridgeClient(CodexProcessManager())
