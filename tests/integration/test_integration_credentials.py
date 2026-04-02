from __future__ import annotations

import asyncio
import json
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
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'integration_credentials.db').as_posix()}"


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
                runtime_status="offline",
                last_heartbeat_at=None,
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
                title="Integration credentials",
                goal="Exercise credential lifecycle",
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


def _seed_job(database_url: str, *, job_id: str, session_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id="agt_builder",
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Public task",
                instructions="Public task",
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


def _prepare_app(tmp_path: Path, monkeypatch) -> tuple[str, object]:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "service-token")
    monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    app_main.get_config.cache_clear()
    _migrate(database_url)
    return database_url, app_main.create_app()


def _operator_headers() -> dict[str, str]:
    return {
        "X-Access-Token": "service-token",
        "X-Actor-Id": "ops_01",
        "X-Actor-Role": "operator",
        "X-Actor-Type": "human",
        "X-Actor-Label": "Oncall operator",
    }


def _assert_forbidden_response(
    response,
    *,
    reason: str | None = None,
    credential_id: str,
    required_scope: str | None = None,
) -> None:
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "access_forbidden"
    details = body["error"]["details"]
    assert details["credential_id"] == credential_id
    if reason is not None:
        assert details["reason"] == reason
    if required_scope is not None:
        assert details["required_scope"] == required_scope


def test_integration_credentials_lifecycle_and_authz(tmp_path, monkeypatch) -> None:
    database_url, app = _prepare_app(tmp_path, monkeypatch)
    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_public")
    _seed_job(database_url, job_id="job_public", session_id="ses_public")

    try:
        with TestClient(app) as client:
            operator_headers = _operator_headers()

            public_principal_response = client.post(
                "/api/v1/operator/integration-principals",
                headers=operator_headers,
                json={
                    "display_label": "Public integration client",
                    "principal_type": "integration_client",
                    "actor_role": "integration_client",
                    "actor_type": "service",
                    "default_scopes": ["public_read"],
                    "notes": "Public A2A client",
                },
            )
            assert public_principal_response.status_code == 201
            public_principal = public_principal_response.json()["principal"]

            operator_principal_response = client.post(
                "/api/v1/operator/integration-principals",
                headers=operator_headers,
                json={
                    "display_label": "Operator automation",
                    "principal_type": "service_account",
                    "actor_role": "operator",
                    "actor_type": "service",
                    "notes": "Operator surface automation",
                },
            )
            assert operator_principal_response.status_code == 201
            operator_principal = operator_principal_response.json()["principal"]
            assert operator_principal["default_scopes"] == ["operator_write"]

            principals_response = client.get(
                "/api/v1/operator/integration-principals",
                headers=operator_headers,
            )
            assert principals_response.status_code == 200
            principal_ids = {
                principal["id"] for principal in principals_response.json()["principals"]
            }
            assert principal_ids == {public_principal["id"], operator_principal["id"]}

            public_read_issue_response = client.post(
                f"/api/v1/operator/integration-principals/{public_principal['id']}/credentials",
                headers=operator_headers,
                json={
                    "label": "read-only client",
                    "scopes": ["public_read"],
                },
            )
            assert public_read_issue_response.status_code == 201
            public_read_credential = public_read_issue_response.json()["credential"]
            public_read_secret = public_read_issue_response.json()["secret_value"]

            public_write_issue_response = client.post(
                f"/api/v1/operator/integration-principals/{public_principal['id']}/credentials",
                headers=operator_headers,
                json={
                    "label": "write client",
                    "scopes": ["public_write"],
                },
            )
            assert public_write_issue_response.status_code == 201
            public_write_credential = public_write_issue_response.json()["credential"]
            public_write_secret = public_write_issue_response.json()["secret_value"]

            operator_issue_response = client.post(
                f"/api/v1/operator/integration-principals/{operator_principal['id']}/credentials",
                headers=operator_headers,
            )
            assert operator_issue_response.status_code == 201
            operator_credential = operator_issue_response.json()["credential"]
            operator_secret = operator_issue_response.json()["secret_value"]

            public_credentials_response = client.get(
                f"/api/v1/operator/integration-principals/{public_principal['id']}/credentials",
                headers=operator_headers,
            )
            assert public_credentials_response.status_code == 200
            public_credentials = public_credentials_response.json()["credentials"]
            public_status_by_id = {
                credential["id"]: credential["status"] for credential in public_credentials
            }
            assert public_status_by_id == {
                public_read_credential["id"]: "active",
                public_write_credential["id"]: "active",
            }

            operator_credentials_response = client.get(
                f"/api/v1/operator/integration-principals/{operator_principal['id']}/credentials",
                headers=operator_headers,
            )
            assert operator_credentials_response.status_code == 200
            operator_credentials = operator_credentials_response.json()["credentials"]
            assert {
                credential["id"]: credential["status"] for credential in operator_credentials
            } == {
                operator_credential["id"]: "active",
            }

            public_list_response = client.get(
                "/api/v1/a2a/tasks",
                headers={"Authorization": f"Bearer {public_read_secret}"},
            )
            assert public_list_response.status_code == 200
            assert public_list_response.json()["tasks"] == []

            public_write_forbidden = client.post(
                "/api/v1/a2a/tasks",
                headers={"Authorization": f"Bearer {public_read_secret}"},
                json={"job_id": "job_public"},
            )
            _assert_forbidden_response(
                public_write_forbidden,
                credential_id=public_read_credential["id"],
                required_scope="public_write",
            )

            public_task_response = client.post(
                "/api/v1/a2a/tasks",
                headers={"Authorization": f"Bearer {public_write_secret}"},
                json={"job_id": "job_public"},
            )
            assert public_task_response.status_code == 201
            assert public_task_response.json()["task"]["job_id"] == "job_public"

            events = asyncio.run(SessionEventRepository(database_url).list_by_session("ses_public"))
            projected_event = next(
                event for event in events if event.event_type == "public.task.projected"
            )
            projected_payload = json.loads(projected_event.event_payload_json or "{}")
            assert projected_event.actor_type == "integration_client"
            assert projected_event.actor_id == public_principal["id"]
            assert projected_payload["actor"]["principal_id"] == public_principal["id"]
            assert projected_payload["actor"]["credential_id"] == public_write_credential["id"]

            operator_dashboard_response = client.get(
                "/api/v1/operator/dashboard",
                headers={"Authorization": f"Bearer {operator_secret}"},
            )
            assert operator_dashboard_response.status_code == 200

            operator_rotate_response = client.post(
                f"/api/v1/operator/integration-credentials/{operator_credential['id']}/rotate",
                headers=operator_headers,
            )
            assert operator_rotate_response.status_code == 200
            rotated_operator_credential = operator_rotate_response.json()["credential"]
            rotated_operator_secret = operator_rotate_response.json()["secret_value"]
            assert (
                operator_rotate_response.json()["replaced_credential_id"]
                == operator_credential["id"]
            )

            old_operator_denied = client.get(
                "/api/v1/operator/dashboard",
                headers={"Authorization": f"Bearer {operator_secret}"},
            )
            _assert_forbidden_response(
                old_operator_denied,
                reason="revoked",
                credential_id=operator_credential["id"],
            )

            rotated_operator_allowed = client.get(
                "/api/v1/operator/dashboard",
                headers={"Authorization": f"Bearer {rotated_operator_secret}"},
            )
            assert rotated_operator_allowed.status_code == 200

            revoke_response = client.post(
                f"/api/v1/operator/integration-credentials/{public_read_credential['id']}/revoke",
                headers=operator_headers,
            )
            assert revoke_response.status_code == 200
            assert revoke_response.json()["credential"]["status"] == "revoked"

            expire_response = client.post(
                f"/api/v1/operator/integration-credentials/{public_write_credential['id']}/expire",
                headers=operator_headers,
            )
            assert expire_response.status_code == 200
            assert expire_response.json()["credential"]["status"] == "expired"

            revoked_public_read = client.get(
                "/api/v1/a2a/tasks",
                headers={"Authorization": f"Bearer {public_read_secret}"},
            )
            _assert_forbidden_response(
                revoked_public_read,
                reason="revoked",
                credential_id=public_read_credential["id"],
            )

            expired_public_write = client.post(
                "/api/v1/a2a/tasks",
                headers={"Authorization": f"Bearer {public_write_secret}"},
                json={"job_id": "job_public"},
            )
            _assert_forbidden_response(
                expired_public_write,
                reason="expired",
                credential_id=public_write_credential["id"],
            )

            public_credentials_after = client.get(
                f"/api/v1/operator/integration-principals/{public_principal['id']}/credentials",
                headers=operator_headers,
            )
            assert public_credentials_after.status_code == 200
            public_status_after = {
                credential["id"]: credential["status"]
                for credential in public_credentials_after.json()["credentials"]
            }
            assert public_status_after == {
                public_read_credential["id"]: "revoked",
                public_write_credential["id"]: "expired",
            }

            operator_credentials_after = client.get(
                f"/api/v1/operator/integration-principals/{operator_principal['id']}/credentials",
                headers=operator_headers,
            )
            assert operator_credentials_after.status_code == 200
            operator_status_after = {
                credential["id"]: credential["status"]
                for credential in operator_credentials_after.json()["credentials"]
            }
            assert operator_status_after == {
                operator_credential["id"]: "revoked",
                rotated_operator_credential["id"]: "active",
            }
    finally:
        app_main.get_config.cache_clear()
