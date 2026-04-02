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
        "STATUS.md",
        "IMPLEMENTATION_TASKS_V5.md",
        "IMPLEMENTATION_ORDER_V5.md",
        "AGENTS.md",
    )

    _write(source_root / "app" / "__init__.py")
    _write(source_root / "docs" / "guide.md")
    _write(source_root / "scripts" / "run.ps1", "Write-Host 'run'")
    _write(source_root / "README.md")
    _write(source_root / "Dockerfile")
    _write(source_root / "pyproject.toml")
    _write(source_root / ".env.example")
    _write(source_root / "STATUS.md")
    _write(source_root / "IMPLEMENTATION_TASKS_V5.md")
    _write(source_root / "IMPLEMENTATION_ORDER_V5.md")
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
    assert manifest["release"]["track"] == "V5"
    assert manifest["release"]["version"] == APP_VERSION
    assert manifest["release"]["tag"] == RELEASE_TAG
    assert manifest["release"]["candidate"] == RELEASE_CANDIDATE
    assert manifest["release"]["baseline_name"] == (
        f"codex-collaboration-coordinator-{APP_VERSION}"
    )
    assert manifest["profile_defaults"]["database_url"] == "sqlite:///./data/codex_coordinator.db"
    assert "profiles/small-team.env" in manifest["included_paths"]
    assert manifest["startup"]["health_check"] == "/api/v1/healthz"
    assert "package bundle created" in manifest["verification"]["checklist"]

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert f"{result.package_name}/release-manifest.json" in names
        assert f"{result.package_name}/profiles/small-team.env" in names
        assert f"{result.package_name}/README.md" in names
