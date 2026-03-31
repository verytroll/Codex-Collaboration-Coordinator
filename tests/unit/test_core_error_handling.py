from __future__ import annotations

import logging
from io import StringIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import install_error_handlers
from app.core.logging import RequestIdFilter, get_logger, reset_request_id, set_request_id
from app.core.middleware import RequestIdMiddleware


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    return app


def test_request_id_is_propagated_on_success() -> None:
    app = build_test_app()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ping", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert response.json() == {"status": "ok"}


def test_http_exception_uses_standard_error_envelope() -> None:
    app = build_test_app()
    client = TestClient(app)

    response = client.get("/missing", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "req-404"
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Not Found",
            "request_id": "req-404",
            "details": None,
        }
    }


def test_validation_error_uses_standard_error_envelope() -> None:
    app = build_test_app()

    class Payload(BaseModel):
        name: str

    @app.post("/payload")
    async def create_payload(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    client = TestClient(app)
    response = client.post("/payload", json={}, headers={"X-Request-ID": "req-422"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["request_id"] == "req-422"
    assert isinstance(body["error"]["details"], list)


def test_request_id_filter_injects_context_value() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(request_id)s %(message)s"))
    handler.addFilter(RequestIdFilter())

    logger = get_logger("app.test")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    token = set_request_id("req-log")
    try:
        logger.info("hello")
    finally:
        reset_request_id(token)

    assert stream.getvalue().strip() == "req-log hello"
