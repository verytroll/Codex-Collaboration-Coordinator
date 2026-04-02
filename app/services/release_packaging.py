"""Release bundle packaging for small-team deployment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app.core.config import (
    DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM,
    VALID_DEPLOYMENT_PROFILES,
    DeploymentProfileDefaults,
    get_deployment_profile_defaults,
)
from app.core.version import (
    APP_VERSION,
    RELEASE_BASELINE_NAME,
    RELEASE_CANDIDATE,
    RELEASE_TAG,
)

RELEASE_PACKAGE_INCLUDE_PATHS = (
    "app",
    "docs",
    "scripts",
    "README.md",
    "Dockerfile",
    "pyproject.toml",
    ".env.example",
    "docs/planning/STATUS.md",
    "docs/planning/archive/PLAN_V7.md",
    "docs/planning/archive/IMPLEMENTATION_TASKS_V7.md",
    "docs/planning/archive/IMPLEMENTATION_ORDER_V7.md",
    "docs/releases/RELEASE_NOTES_V7.md",
    "docs/releases/UPGRADE_NOTES_V7.md",
    "AGENTS.md",
)
RELEASE_PACKAGE_IGNORE_PATTERNS = (
    "__pycache__",
    "*.pyc",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "data",
)


@dataclass(frozen=True, slots=True)
class ReleasePackageResult:
    """Paths for a generated release bundle."""

    package_name: str
    package_dir: str
    archive_path: str
    manifest_path: str
    profile_env_path: str


def _normalize_profile(deployment_profile: str | None) -> str:
    if deployment_profile is None or not deployment_profile.strip():
        return DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM
    normalized = deployment_profile.strip().lower()
    if normalized in VALID_DEPLOYMENT_PROFILES:
        return normalized
    return DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM


def _copy_package_tree(
    source_root: Path,
    package_root: Path,
    include_paths: Sequence[str],
) -> list[str]:
    included: list[str] = []
    for relative_path in include_paths:
        source_path = source_root / relative_path
        destination_path = package_root / relative_path
        if not source_path.exists():
            continue
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                destination_path,
                ignore=shutil.ignore_patterns(*RELEASE_PACKAGE_IGNORE_PATTERNS),
            )
        else:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        included.append(relative_path)
    return included


def _build_profile_env_lines(
    deployment_profile: str,
    profile_defaults: DeploymentProfileDefaults,
) -> list[str]:
    runtime_recovery_enabled = "true" if profile_defaults.runtime_recovery_enabled else "false"
    return [
        f"APP_ENV={profile_defaults.app_env}",
        f"APP_HOST={profile_defaults.app_host}",
        "APP_PORT=8000",
        f"APP_RELOAD={'true' if profile_defaults.app_reload else 'false'}",
        f"DATABASE_URL={profile_defaults.database_url}",
        "CODEX_BRIDGE_MODE=local",
        f"ACCESS_BOUNDARY_MODE={profile_defaults.access_boundary_mode}",
        f"DEPLOYMENT_PROFILE={deployment_profile}",
        f"RUNTIME_RECOVERY_ENABLED={runtime_recovery_enabled}",
        f"RUNTIME_RECOVERY_INTERVAL_SECONDS={profile_defaults.runtime_recovery_interval_seconds:g}",
        f"RUNTIME_STALE_AFTER_MINUTES={profile_defaults.runtime_stale_after_minutes}",
    ]


def _build_release_metadata(
    *,
    package_name: str,
    deployment_profile: str,
) -> dict[str, object]:
    return {
        "track": "V7",
        "version": APP_VERSION,
        "tag": RELEASE_TAG,
        "candidate": RELEASE_CANDIDATE,
        "package_name": package_name,
        "baseline_name": RELEASE_BASELINE_NAME,
        "deployment_profile": deployment_profile,
    }


def build_release_package(
    source_root: Path,
    output_dir: Path,
    *,
    deployment_profile: str | None = None,
    include_paths: Sequence[str] = RELEASE_PACKAGE_INCLUDE_PATHS,
) -> ReleasePackageResult:
    """Build a curated release bundle and archive it."""
    normalized_profile = _normalize_profile(deployment_profile)
    profile_defaults = get_deployment_profile_defaults(normalized_profile)
    package_name = f"codex-collaboration-coordinator-{APP_VERSION}-{normalized_profile}"
    package_root = output_dir / package_name
    archive_path = output_dir / f"{package_name}.zip"
    manifest_path = package_root / "release-manifest.json"
    profile_env_path = package_root / "profiles" / f"{normalized_profile}.env"

    if package_root.exists():
        shutil.rmtree(package_root)
    if archive_path.exists():
        archive_path.unlink()

    package_root.mkdir(parents=True, exist_ok=True)
    included_paths = _copy_package_tree(source_root, package_root, include_paths)

    profile_env_path.parent.mkdir(parents=True, exist_ok=True)
    profile_env_path.write_text(
        "\n".join(_build_profile_env_lines(normalized_profile, profile_defaults)) + "\n"
    )

    manifest = {
        "package_name": package_name,
        "app_version": APP_VERSION,
        "deployment_profile": normalized_profile,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "release": _build_release_metadata(
            package_name=package_name,
            deployment_profile=normalized_profile,
        ),
        "profile_defaults": asdict(profile_defaults),
        "included_paths": sorted(included_paths + [f"profiles/{normalized_profile}.env"]),
        "verification": {
            "checklist": [
                "package bundle created",
                "manifest and profile env match the small-team baseline",
                "release metadata records the V7 baseline version, tag, and candidate",
                "smoke gate passes against the running release runtime",
                "health, readiness, operator shell, live activity, and public A2A flow are checked",
                "A2A conformance verifies the supported early-adopter handoff surface",
            ]
        },
        "startup": {
            "script": ".\\scripts\\run.ps1",
            "container": "docker run --rm -p 8000:8000 ...",
            "health_check": "/api/v1/healthz",
            "readiness_check": "/api/v1/readinessz",
            "durable_runtime": {
                "enabled": profile_defaults.runtime_recovery_enabled,
                "recovery_interval_seconds": profile_defaults.runtime_recovery_interval_seconds,
                "stale_after_minutes": profile_defaults.runtime_stale_after_minutes,
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in package_root.rglob("*"):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(output_dir))

    return ReleasePackageResult(
        package_name=package_name,
        package_dir=str(package_root),
        archive_path=str(archive_path),
        manifest_path=str(manifest_path),
        profile_env_path=str(profile_env_path),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Package the release bundle from the repository root."""
    parser = argparse.ArgumentParser(description="Build the small-team release bundle.")
    parser.add_argument(
        "--source-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root to package",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("dist") / "release"),
        help="Directory where the bundle and archive will be written",
    )
    parser.add_argument(
        "--deployment-profile",
        default=os.getenv("DEPLOYMENT_PROFILE", DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM),
        help="Deployment profile to package",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = build_release_package(
        source_root=Path(args.source_root),
        output_dir=Path(args.output_dir),
        deployment_profile=args.deployment_profile,
    )
    print(f"{result.package_name} archive={result.archive_path} manifest={result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
