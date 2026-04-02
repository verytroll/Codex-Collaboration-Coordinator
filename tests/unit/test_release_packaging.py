from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.core.version import APP_VERSION, RELEASE_CANDIDATE, RELEASE_TAG
from app.services.release_packaging import build_release_package


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_build_release_package_writes_manifest_and_archive(tmp_path) -> None:
    source_root = tmp_path / "source"
    output_dir = tmp_path / "dist"
    include_paths = (
        "app",
        "docs",
        "scripts",
        "README.md",
        "Dockerfile",
        "pyproject.toml",
        ".env.example",
        "docs/planning/STATUS.md",
        "docs/planning/PLAN_V7.md",
        "docs/planning/IMPLEMENTATION_TASKS_V7.md",
        "docs/planning/IMPLEMENTATION_ORDER_V7.md",
        "docs/releases/RELEASE_NOTES_V7.md",
        "docs/releases/UPGRADE_NOTES_V7.md",
        "AGENTS.md",
    )

    _write(source_root / "app" / "__init__.py")
    _write(source_root / "docs" / "guide.md")
    _write(source_root / "scripts" / "run.ps1", "Write-Host 'run'")
    _write(source_root / "README.md")
    _write(source_root / "Dockerfile")
    _write(source_root / "pyproject.toml")
    _write(source_root / ".env.example")
    _write(source_root / "docs/planning/STATUS.md")
    _write(source_root / "docs/planning/PLAN_V7.md")
    _write(source_root / "docs/planning/IMPLEMENTATION_TASKS_V7.md")
    _write(source_root / "docs/planning/IMPLEMENTATION_ORDER_V7.md")
    _write(source_root / "docs/releases/RELEASE_NOTES_V7.md")
    _write(source_root / "docs/releases/UPGRADE_NOTES_V7.md")
    _write(source_root / "AGENTS.md")

    result = build_release_package(
        source_root,
        output_dir,
        deployment_profile="small-team",
        include_paths=include_paths,
    )

    manifest_path = Path(result.manifest_path)
    archive_path = Path(result.archive_path)
    profile_env_path = Path(result.profile_env_path)

    assert result.package_name.endswith("-small-team")
    assert manifest_path.exists()
    assert archive_path.exists()
    assert profile_env_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["app_version"] == APP_VERSION
    assert manifest["deployment_profile"] == "small-team"
    assert manifest["release"]["package_name"] == result.package_name
    assert manifest["release"]["track"] == "V7"
    assert manifest["release"]["version"] == APP_VERSION
    assert manifest["release"]["tag"] == RELEASE_TAG
    assert manifest["release"]["candidate"] == RELEASE_CANDIDATE
    assert manifest["release"]["baseline_name"] == (
        f"codex-collaboration-coordinator-{APP_VERSION}"
    )
    assert manifest["profile_defaults"]["database_url"] == "sqlite:///./data/codex_coordinator.db"
    assert manifest["profile_defaults"]["runtime_recovery_enabled"] is True
    assert manifest["profile_defaults"]["runtime_recovery_interval_seconds"] == 15.0
    assert manifest["profile_defaults"]["runtime_stale_after_minutes"] == 10
    assert "docs/planning/PLAN_V7.md" in manifest["included_paths"]
    assert "docs/planning/IMPLEMENTATION_TASKS_V7.md" in manifest["included_paths"]
    assert "docs/planning/IMPLEMENTATION_ORDER_V7.md" in manifest["included_paths"]
    assert "docs/releases/RELEASE_NOTES_V7.md" in manifest["included_paths"]
    assert "docs/releases/UPGRADE_NOTES_V7.md" in manifest["included_paths"]
    assert "profiles/small-team.env" in manifest["included_paths"]
    assert manifest["startup"]["health_check"] == "/api/v1/healthz"
    assert manifest["startup"]["durable_runtime"]["enabled"] is True
    assert manifest["startup"]["durable_runtime"]["recovery_interval_seconds"] == 15
    assert manifest["startup"]["durable_runtime"]["stale_after_minutes"] == 10
    assert "package bundle created" in manifest["verification"]["checklist"]
    assert (
        "release metadata records the V7 baseline version, tag, and candidate"
        in manifest["verification"]["checklist"]
    )
    assert (
        "A2A conformance verifies the supported early-adopter handoff surface"
        in manifest["verification"]["checklist"]
    )
    profile_env_text = profile_env_path.read_text()
    assert "RUNTIME_RECOVERY_ENABLED=true" in profile_env_text
    assert "RUNTIME_RECOVERY_INTERVAL_SECONDS=15" in profile_env_text
    assert "RUNTIME_STALE_AFTER_MINUTES=10" in profile_env_text

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert f"{result.package_name}/release-manifest.json" in names
        assert f"{result.package_name}/profiles/small-team.env" in names
        assert f"{result.package_name}/README.md" in names
