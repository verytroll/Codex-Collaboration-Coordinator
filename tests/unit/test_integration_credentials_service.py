from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.integration_credentials import (
    IntegrationCredentialRepository,
    IntegrationPrincipalRecord,
    IntegrationPrincipalRepository,
)
from app.services.integration_credentials import IntegrationCredentialService


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'integration_credentials.db').as_posix()}"


def _prepare_service(tmp_path: Path) -> tuple[str, IntegrationCredentialService]:
    database_url = _database_url(tmp_path)
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))
    return (
        database_url,
        IntegrationCredentialService(
            principal_repository=IntegrationPrincipalRepository(database_url),
            credential_repository=IntegrationCredentialRepository(database_url),
        ),
    )


def _create_operator_principal(service: IntegrationCredentialService) -> IntegrationPrincipalRecord:
    return asyncio.run(
        service.create_principal(
            display_label="Operator automation",
            principal_type="service_account",
            actor_role="operator",
            actor_type="service",
        )
    )


def test_issue_and_rotate_preserve_explicit_empty_scopes(tmp_path) -> None:
    _, service = _prepare_service(tmp_path)
    principal = _create_operator_principal(service)

    issued = asyncio.run(
        service.issue_credential(
            principal_id=principal.id,
            scopes=[],
        )
    )
    assert json.loads(issued.credential.scopes_json) == []

    source = asyncio.run(
        service.issue_credential(
            principal_id=principal.id,
            scopes=["public_write"],
        )
    )
    assert json.loads(source.credential.scopes_json) == ["public_write"]

    rotated = asyncio.run(
        service.rotate_credential(
            source.credential.id,
            scopes=[],
        )
    )
    assert json.loads(rotated.credential.scopes_json) == []


def test_issue_credential_rejects_timezone_less_expires_at(tmp_path) -> None:
    _, service = _prepare_service(tmp_path)
    principal = _create_operator_principal(service)

    with pytest.raises(ValueError):
        asyncio.run(
            service.issue_credential(
                principal_id=principal.id,
                expires_at="2026-04-02T00:00:00",
            )
        )


def test_authenticate_secret_rejects_malformed_expires_at_without_crashing(
    tmp_path,
    monkeypatch,
) -> None:
    _, service = _prepare_service(tmp_path)
    principal = _create_operator_principal(service)

    monkeypatch.setattr(
        "app.services.integration_credentials.secrets.token_urlsafe",
        lambda _size: "fixed-secret-value",
    )
    issued = asyncio.run(service.issue_credential(principal_id=principal.id))

    credential = asyncio.run(service.get_credential(issued.credential.id))
    malformed = replace(credential, expires_at="2026-04-02T00:00:00")
    asyncio.run(service.credential_repository.update(malformed))

    match = asyncio.run(
        service.authenticate_secret(
            "fixed-secret-value",
            surface="public",
            auth_mode="protected",
        )
    )

    assert match is not None
    assert match.status == "invalid_expires_at"
    assert match.credential is not None
    assert match.credential.id == issued.credential.id


def test_rotate_credential_rolls_back_on_secret_collision(tmp_path, monkeypatch) -> None:
    _, service = _prepare_service(tmp_path)
    principal = _create_operator_principal(service)

    monkeypatch.setattr(
        "app.services.integration_credentials.secrets.token_urlsafe",
        lambda _size: "collision-secret",
    )
    issued = asyncio.run(service.issue_credential(principal_id=principal.id))

    with pytest.raises(sqlite3.IntegrityError):
        asyncio.run(service.rotate_credential(issued.credential.id))

    current = asyncio.run(service.get_credential(issued.credential.id))
    assert current.status == "active"
    assert current.revoked_at is None

    credentials = asyncio.run(service.list_credentials(principal_id=principal.id))
    assert [credential.id for credential in credentials] == [issued.credential.id]
