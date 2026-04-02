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
from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'a2a_conformance.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(database_url: str, *, agent_id: str, display_name: str, is_lead: bool) -> None:
    created_at = "2026-04-02T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=display_name,
                role="planner" if is_lead else "builder",
                is_lead_default=1 if is_lead else 0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str, lead_agent_id: str) -> None:
    created_at = "2026-04-02T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title="A2A conformance",
                goal="Exercise the supported early-adopter A2A baseline",
                status="active",
                lead_agent_id=lead_agent_id,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                template_key=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_job(database_url: str, *, session_id: str, job_id: str, agent_id: str) -> None:
    created_at = "2026-04-02T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="A2A conformance job",
                instructions="Exercise the supported public A2A baseline",
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
                started_at=None,
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
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        self.lock = threading.Lock()


def _make_handler(state: _ReceiverState):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            with state.lock:
                state.requests.append({"headers": dict(self.headers), "body": body})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return Handler


def test_early_adopter_a2a_conformance_path_matches_supported_claims(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "service-token")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS", "2")
    app_main.get_config.cache_clear()
    _migrate(database_url)

    _seed_agent(database_url, agent_id="agt_lead", display_name="Lead", is_lead=True)
    _seed_agent(database_url, agent_id="agt_builder", display_name="Builder", is_lead=False)
    _seed_session(database_url, session_id="ses_a2a", lead_agent_id="agt_lead")
    _seed_job(
        database_url,
        session_id="ses_a2a",
        job_id="job_a2a_conformance",
        agent_id="agt_builder",
    )

    state = _ReceiverState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target_url = f"http://127.0.0.1:{server.server_port}/hook"

    app = app_main.create_app()
    try:
        with TestClient(app) as client:
            principal_response = client.post(
                "/api/v1/operator/integration-principals",
                headers=_operator_headers(),
                json={
                    "display_label": "A2A Conformance",
                    "principal_type": "service_account",
                    "actor_role": "operator",
                    "actor_type": "service",
                    "default_scopes": ["operator_write"],
                },
            )
            assert principal_response.status_code == 201
            principal_id = principal_response.json()["principal"]["id"]

            credential_response = client.post(
                f"/api/v1/operator/integration-principals/{principal_id}/credentials",
                headers=_operator_headers(),
                json={
                    "label": "a2a-conformance",
                    "scopes": ["operator_write"],
                },
            )
            assert credential_response.status_code == 201
            credential_secret = credential_response.json()["secret_value"]
            assert credential_secret
            credential_headers = {"Authorization": f"Bearer {credential_secret}"}

            agent_card_response = client.get(
                "/.well-known/agent-card.json",
                headers=credential_headers,
            )
            assert agent_card_response.status_code == 200
            agent_card = agent_card_response.json()
            endpoint_paths = {endpoint["path"] for endpoint in agent_card["endpoints"]}
            assert "/api/v1/a2a/tasks" in endpoint_paths
            assert "/api/v1/a2a/tasks/{task_id}/events" in endpoint_paths
            assert "/api/v1/a2a/subscriptions/{subscription_id}/events" in endpoint_paths
            assert "/api/v1/a2a/jobs/{job_id}/project" not in endpoint_paths
            notes = " ".join(agent_card["compatibility_notes"]).lower()
            assert "managed integration credentials" in notes
            assert "outbound webhooks" in notes
            assert "compatibility only" in notes

            create_task_response = client.post(
                "/api/v1/a2a/tasks",
                headers=credential_headers,
                json={"job_id": "job_a2a_conformance"},
            )
            assert create_task_response.status_code == 201
            task = create_task_response.json()["task"]
            assert task["contract_version"] == "a2a.public.task.v1"
            task_id = task["task_id"]

            list_response = client.get(
                "/api/v1/a2a/tasks",
                headers=credential_headers,
                params={"session_id": "ses_a2a"},
            )
            assert list_response.status_code == 200
            assert [item["task_id"] for item in list_response.json()["tasks"]] == [task_id]

            get_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}",
                headers=credential_headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["task"]["task_id"] == task_id

            subscription_response = client.post(
                f"/api/v1/a2a/tasks/{task_id}/subscriptions",
                headers=credential_headers,
                json={"since_sequence": 0},
            )
            assert subscription_response.status_code == 201
            subscription = subscription_response.json()["subscription"]
            assert subscription["contract_version"] == "a2a.public.task.subscription.v1"

            subscription_get_response = client.get(
                f"/api/v1/a2a/subscriptions/{subscription['subscription_id']}",
                headers=credential_headers,
            )
            assert subscription_get_response.status_code == 200
            assert (
                subscription_get_response.json()["subscription"]["subscription_id"]
                == subscription["subscription_id"]
            )

            initial_events_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                headers=credential_headers,
                params={"since_sequence": 0},
            )
            assert initial_events_response.status_code == 200
            initial_events = initial_events_response.json()["events"]
            assert [event["event_type"] for event in initial_events] == ["created"]
            assert initial_events[0]["contract_version"] == "a2a.public.task.event.v1"

            stream_response = client.get(
                f"/api/v1/a2a/subscriptions/{subscription['subscription_id']}/events",
                headers=credential_headers,
            )
            assert stream_response.status_code == 200
            assert stream_response.headers["content-type"].startswith("text/event-stream")
            assert '"contract_version": "a2a.public.task.event.stream.v1"' in stream_response.text

            webhook_response = client.post(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhooks",
                headers=credential_headers,
                json={"target_url": target_url, "signing_secret": "conformance-secret"},
            )
            assert webhook_response.status_code == 201
            assert webhook_response.json()["webhook"]["status"] == "active"

            job_repository = JobRepository(database_url)
            job = asyncio.run(job_repository.get("job_a2a_conformance"))
            assert job is not None
            asyncio.run(
                job_repository.update(
                    replace(
                        job,
                        status="canceled",
                        updated_at="2026-04-02T00:01:00Z",
                        error_code="manual_cancel",
                        error_message="Canceled by conformance fixture.",
                    )
                )
            )

            refresh_response = client.post(
                "/api/v1/a2a/tasks",
                headers=credential_headers,
                json={"job_id": "job_a2a_conformance"},
            )
            assert refresh_response.status_code == 201

            deadline = time.time() + 5
            while time.time() < deadline:
                with state.lock:
                    if state.requests:
                        break
                time.sleep(0.1)
            with state.lock:
                assert len(state.requests) == 1
                webhook_request = state.requests[0]
            headers = webhook_request["headers"]
            body = webhook_request["body"]
            assert headers["X-CCC-Task-Id"] == task_id
            assert int(headers["X-CCC-Event-Sequence"]) >= 2
            expected_signature = (
                "sha256="
                + hmac.new(
                    b"conformance-secret",
                    str(body).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
            )
            assert headers["X-CCC-Signature"] == expected_signature

            deliveries_response = client.get(
                f"/api/v1/operator/a2a/tasks/{task_id}/webhook-deliveries",
                headers=credential_headers,
            )
            assert deliveries_response.status_code == 200
            deliveries = deliveries_response.json()["deliveries"]
            assert len(deliveries) == 1
            assert deliveries[0]["status"] == "delivered"
            assert deliveries[0]["attempt_count"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        app_main.get_config.cache_clear()
