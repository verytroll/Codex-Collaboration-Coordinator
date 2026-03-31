"""Application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_config
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware

APP_NAME = "codex-collaboration-coordinator"
APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = get_config()
    configure_logging(settings.log_level)

    app = FastAPI(title=APP_NAME, version=APP_VERSION)
    app.add_middleware(RequestIdMiddleware, header_name=settings.request_id_header)
    install_error_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
