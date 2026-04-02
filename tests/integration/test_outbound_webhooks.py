from __future__ import annotations

import asyncio
import hashlib
import hmac
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'outbound_webhooks.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(database_url: str, *, agent_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=agent_id,
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )
    asyncio.run(
        AgentRuntimeRepository(database_url).create(
            AgentRuntimeRecord(
                id=f"rt_{agent_id}",
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status="online",
                last_heartbeat_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title="Outbound webhooks",
                goal="Exercise outbound webhook delivery",
                status="active",
                lead_agent_id="agt_lead",
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                template_key="template",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_job(database_url: str, *, session_id: str, job_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id="agt_builder",
                runtime_id="rt_agt_builder",
                source_message_id=None,
                parent_job_id=None,
                title="Outbound public task",
                instructions="Project to public task and webhook",
                status="queued",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="queued",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=created_at,
                completed_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _operator_headers() -> dict[str, str]:
    return {
        "X-Access-Token": "service-token",
        "X-Actor-Id": "ops_01",
        "X-Actor-Role": "operator",
        "X-Actor-Type": "human",
        "X-Actor-Label": "Oncall operator",
    }


class _ReceiverState:
    def __init__(self, responses: list[int] | None = None) -> None:
        self.responses = list(responses) if responses is not None else [500, 200]
        self.requests: list[dict[str, object]] = []
        self.lock = threading.Lock()


def _make_handler(state: _ReceiverState):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            with state.lock:
                state.requests.append({"headers": dict(self.headers), "body": body})
                status_code = state.responses.pop(0) if state.responses else 200
            self.send_response(status_code)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return Handler


def test_outbound_webhook_delivery_retry_and_recovery(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "service-token")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS", "2")
    app_main.get_config.cache_clear()
    _migrate(database_url)

    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_public")
    _seed_job(database_url, session_id="ses_public", job_id="job_public")

    state = _ReceiverState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target_url = f"http://127.0.0.1:{server.server_port}/hook"

    app = app_main.create_app()
    try:
        with TestClient(app) as client:
            create_task_response = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert create_task_response.status_code == 201
            task_id = create_task_response.json()["task"]["task_id"]

            webhook_response = client.post(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhooks",
                headers=_operator_headers(),
                json={"target_url": target_url, "signing_secret": "test-secret"},
            )
            assert webhook_response.status_code == 201
            registration = webhook_response.json()["webhook"]
            assert registration["status"] == "active"
            assert webhook_response.json()["signing_secret"] == "test-secret"

            job_repository = JobRepository(database_url)
            job = asyncio.run(job_repository.get("job_public"))
            assert job is not None
            updated_job = replace(
                job,
                status="running",
                updated_at="2026-04-01T00:01:00Z",
                result_summary="Started running",
            )
            asyncio.run(job_repository.update(updated_job))

            refresh_response = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert refresh_response.status_code == 201

            deliveries_response = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=_operator_headers(),
            )
            assert deliveries_response.status_code == 200
            deliveries = deliveries_response.json()["deliveries"]
            assert len(deliveries) == 1
            assert deliveries[0]["status"] == "retrying"
            assert deliveries[0]["attempt_count"] == 1

            sweep = asyncio.run(app.state.durable_runtime_supervisor.run_once())
            assert sweep.outbound is not None
            assert sweep.outbound.delivered == 1

            deliveries_after_retry = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=_operator_headers(),
            ).json()["deliveries"]
            assert deliveries_after_retry[0]["status"] == "delivered"
            assert deliveries_after_retry[0]["attempt_count"] == 2

            list_response = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhooks",
                headers=_operator_headers(),
            )
            assert list_response.status_code == 200
            assert len(list_response.json()["webhooks"]) == 1

            disable_response = client.post(
                f"/api/v1/operator/a2a/tasks/webhooks/{registration['id']}/disable",
                headers=_operator_headers(),
                json={"reason": "maintenance"},
            )
            assert disable_response.status_code == 200
            assert disable_response.json()["webhook"]["status"] == "disabled"

            completed_job = replace(
                updated_job,
                status="completed",
                completed_at="2026-04-01T00:02:00Z",
                updated_at="2026-04-01T00:02:00Z",
            )
            asyncio.run(job_repository.update(completed_job))
            completed_refresh = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert completed_refresh.status_code == 201
            final_deliveries = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=_operator_headers(),
            ).json()["deliveries"]
            assert len(final_deliveries) == 1

            assert len(state.requests) == 2
            first_request = state.requests[0]
            body = first_request["body"]
            assert '"event_type":"status_changed"' in body
            headers = first_request["headers"]
            assert headers["X-CCC-Task-Id"] == task_id
            assert headers["X-CCC-Delivery-Attempt"] == "1"
            expected_signature = (
                "sha256="
                + hmac.new(
                    b"test-secret",
                    body.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
            )
            assert headers["X-CCC-Signature"] == expected_signature
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        app_main.get_config.cache_clear()


def test_outbound_webhook_preserves_registration_order_across_retries(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "service-token")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS", "2")
    app_main.get_config.cache_clear()
    _migrate(database_url)

    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_public")
    _seed_job(database_url, session_id="ses_public", job_id="job_public")

    state = _ReceiverState(responses=[500, 200, 200])
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target_url = f"http://127.0.0.1:{server.server_port}/hook"

    app = app_main.create_app()
    try:
        with TestClient(app) as client:
            create_task_response = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert create_task_response.status_code == 201
            task_id = create_task_response.json()["task"]["task_id"]

            webhook_response = client.post(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhooks",
                headers=_operator_headers(),
                json={"target_url": target_url, "signing_secret": "test-secret"},
            )
            assert webhook_response.status_code == 201

            job_repository = JobRepository(database_url)
            job = asyncio.run(job_repository.get("job_public"))
            assert job is not None

            first_update = replace(
                job,
                status="running",
                updated_at="2026-04-01T00:01:00Z",
                result_summary="Started running",
            )
            asyncio.run(job_repository.update(first_update))
            first_refresh = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert first_refresh.status_code == 201
            assert len(state.requests) == 1
            blocked_sequence = int(state.requests[0]["headers"]["X-CCC-Event-Sequence"])

            second_update = replace(
                first_update,
                status="completed",
                completed_at="2026-04-01T00:02:00Z",
                updated_at="2026-04-01T00:02:00Z",
            )
            asyncio.run(job_repository.update(second_update))
            second_refresh = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert second_refresh.status_code == 201

            deliveries_after_second_refresh = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=_operator_headers(),
            ).json()["deliveries"]
            assert len(deliveries_after_second_refresh) >= 2
            assert len(state.requests) == 2
            assert [
                int(request["headers"]["X-CCC-Event-Sequence"]) for request in state.requests
            ] == [blocked_sequence, blocked_sequence]
            assert any(
                delivery["event_sequence"] > blocked_sequence and delivery["status"] == "pending"
                for delivery in deliveries_after_second_refresh
            )

            first_sweep = asyncio.run(app.state.durable_runtime_supervisor.run_once())
            assert first_sweep.outbound is not None
            assert first_sweep.outbound.delivered == 1
            assert first_sweep.outbound.attempted == 1
            assert len(state.requests) == 3
            assert int(state.requests[2]["headers"]["X-CCC-Event-Sequence"]) > blocked_sequence

            second_sweep = asyncio.run(app.state.durable_runtime_supervisor.run_once())
            assert second_sweep.outbound is not None
            assert second_sweep.outbound.attempted <= 1

            delivered_sequences = [
                int(request["headers"]["X-CCC-Event-Sequence"]) for request in state.requests
            ]
            assert delivered_sequences[:2] == [blocked_sequence, blocked_sequence]
            assert delivered_sequences == sorted(delivered_sequences)

            final_deliveries = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=_operator_headers(),
            ).json()["deliveries"]
            assert all(item["status"] == "delivered" for item in final_deliveries)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        app_main.get_config.cache_clear()


def test_outbound_webhook_background_retry_runs_without_runtime_recovery(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "local-dev")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "service-token")
    monkeypatch.setenv("RUNTIME_RECOVERY_ENABLED", "false")
    monkeypatch.setenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", "0.1")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS", "2")
    app_main.get_config.cache_clear()
    _migrate(database_url)

    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_public")
    _seed_job(database_url, session_id="ses_public", job_id="job_public")

    state = _ReceiverState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target_url = f"http://127.0.0.1:{server.server_port}/hook"

    app = app_main.create_app()
    try:
        with TestClient(app) as client:
            create_task_response = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert create_task_response.status_code == 201
            task_id = create_task_response.json()["task"]["task_id"]

            webhook_response = client.post(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhooks",
                headers=_operator_headers(),
                json={"target_url": target_url, "signing_secret": "test-secret"},
            )
            assert webhook_response.status_code == 201

            job_repository = JobRepository(database_url)
            job = asyncio.run(job_repository.get("job_public"))
            assert job is not None
            updated_job = replace(
                job,
                status="running",
                updated_at="2026-04-01T00:01:00Z",
                result_summary="Started running",
            )
            asyncio.run(job_repository.update(updated_job))

            refresh_response = client.post(
                "/api/v1/a2a/tasks",
                headers=_operator_headers(),
                json={"job_id": "job_public"},
            )
            assert refresh_response.status_code == 201
            assert len(state.requests) >= 1

            deadline = time.time() + 3
            final_deliveries: list[dict[str, object]] = []
            while time.time() < deadline:
                final_deliveries = client.get(
                    f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                    headers=_operator_headers(),
                ).json()["deliveries"]
                if final_deliveries and any(
                    delivery["status"] == "delivered" and delivery["attempt_count"] >= 2
                    for delivery in final_deliveries
                ):
                    break
                time.sleep(0.1)

            assert final_deliveries
            assert any(
                delivery["status"] == "delivered" and delivery["attempt_count"] >= 2
                for delivery in final_deliveries
            )
            assert len(state.requests) >= 2
            assert app.state.durable_runtime_supervisor.is_running() is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        app_main.get_config.cache_clear()
