from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'session_templates.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _create_agent(
    client: TestClient,
    *,
    display_name: str,
    role: str,
    is_lead: bool,
) -> str:
    response = client.post(
        "/api/v1/agents",
        json={
            "display_name": display_name,
            "role": role,
            "is_lead": is_lead,
            "runtime_kind": "codex",
            "runtime_config": {
                "workspace_path": "/workspace/project",
                "sandbox_mode": "workspace-write",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["agent"]["id"]


def test_session_template_catalog_create_and_instantiate_flow(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead Planner",
                role="planner",
                is_lead=True,
            )

            list_response = client.get("/api/v1/session-templates")
            assert list_response.status_code == 200
            builtin_keys = [
                template["template_key"] for template in list_response.json()["templates"]
            ]
            assert builtin_keys[:4] == [
                "planning_heavy",
                "implementation_review",
                "research_review",
                "hotfix_triage",
            ]

            create_response = client.post(
                "/api/v1/session-templates",
                json={
                    "template_key": "design_review",
                    "title": "Design Review",
                    "description": "Custom template for design-heavy work",
                    "default_goal": "Review the design and capture follow-up actions.",
                    "participant_roles": ["planner", "designer", "reviewer"],
                    "channels": [
                        {
                            "channel_key": "design",
                            "display_name": "Design",
                            "description": "Design discussion and decisions",
                            "sort_order": 15,
                            "is_default": False,
                        }
                    ],
                    "phase_order": [
                        {"phase_key": "planning", "sort_order": 10},
                        {"phase_key": "implementation", "sort_order": 20},
                        {"phase_key": "review", "sort_order": 30},
                    ],
                    "rule_presets": [
                        {
                            "rule_type": "channel_routing_preference",
                            "name": "Send general to design",
                            "description": "Move general discussion into the design lane.",
                            "priority": 5,
                            "is_active": True,
                            "conditions": {"channel_key": "general"},
                            "actions": {"target_channel_key": "design"},
                        }
                    ],
                    "orchestration": {"default_active_phase_key": "planning"},
                    "is_default": True,
                    "sort_order": 5,
                },
            )
            assert create_response.status_code == 201
            custom_template = create_response.json()["template"]
            assert custom_template["template_key"] == "design_review"
            assert custom_template["participant_roles"] == ["planner", "designer", "reviewer"]

            get_response = client.get("/api/v1/session-templates/design_review")
            assert get_response.status_code == 200
            assert get_response.json()["template"]["title"] == "Design Review"

            instantiate_response = client.post(
                "/api/v1/session-templates/design_review/instantiate",
                json={
                    "lead_agent_id": lead_agent_id,
                },
            )
            assert instantiate_response.status_code == 201
            session_body = instantiate_response.json()["session"]
            assert session_body["title"] == "Design Review"
            assert session_body["goal"] == "Review the design and capture follow-up actions."
            assert session_body["status"] == "active"
            assert session_body["active_phase_id"] is not None

            session_id = session_body["id"]
            channels_response = client.get(f"/api/v1/sessions/{session_id}/channels")
            assert channels_response.status_code == 200
            channel_keys = [
                channel["channel_key"] for channel in channels_response.json()["channels"]
            ]
            assert channel_keys == ["general", "design", "planning", "review", "debug"]

            phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert phases_response.status_code == 200
            phase_keys = [phase["phase_key"] for phase in phases_response.json()["phases"]]
            assert phase_keys == [
                "planning",
                "implementation",
                "review",
                "revise",
                "finalize",
            ]
            assert phases_response.json()["phases"][0]["is_active"] is True

            rules_response = client.get(f"/api/v1/sessions/{session_id}/rules")
            assert rules_response.status_code == 200
            assert [rule["name"] for rule in rules_response.json()["rules"]] == [
                "Send general to design"
            ]
    finally:
        app_main.get_config.cache_clear()


def test_builtin_session_template_instantiation_uses_preset_active_phase(
    tmp_path, monkeypatch
) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead Builder",
                role="builder",
                is_lead=True,
            )

            instantiate_response = client.post(
                "/api/v1/session-templates/implementation_review/instantiate",
                json={
                    "lead_agent_id": lead_agent_id,
                },
            )
            assert instantiate_response.status_code == 201
            session_body = instantiate_response.json()["session"]
            assert session_body["title"] == "Implementation Review"
            assert session_body["status"] == "active"
            assert session_body["active_phase_id"] is not None

            session_id = session_body["id"]
            phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert phases_response.status_code == 200
            phases = phases_response.json()["phases"]
            active_phase = next(phase for phase in phases if phase["is_active"] is True)
            assert active_phase["phase_key"] == "implementation"
            assert [phase["phase_key"] for phase in phases] == [
                "planning",
                "implementation",
                "review",
                "revise",
                "finalize",
            ]
    finally:
        app_main.get_config.cache_clear()
