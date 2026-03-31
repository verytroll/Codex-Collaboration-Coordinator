"""Application entry point."""

from __future__ import annotations

from typing import Any

APP_NAME = "codex-collaboration-coordinator"
APP_VERSION = "0.1.0"

try:
    from fastapi import FastAPI
except ModuleNotFoundError:  # pragma: no cover - optional at skeleton stage
    FastAPI = None  # type: ignore[assignment]


def create_app() -> Any:
    """Create the application object.

    The skeleton keeps this import-safe even before dependencies are wired in.
    """
    if FastAPI is None:
        return {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
        }

    return FastAPI(title=APP_NAME, version=APP_VERSION)


app = create_app()
