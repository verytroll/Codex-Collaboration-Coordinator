from __future__ import annotations

from importlib import import_module
from pathlib import Path


def test_skeleton_directories_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    expected_directories = [
        root / "app",
        root / "app" / "api",
        root / "app" / "core",
        root / "app" / "db",
        root / "app" / "repositories",
        root / "app" / "services",
        root / "app" / "codex_bridge",
        root / "app" / "models",
        root / "tests" / "unit",
        root / "tests" / "integration",
        root / "scripts",
    ]

    for directory in expected_directories:
        assert directory.is_dir(), f"Missing directory: {directory}"


def test_app_main_is_importable() -> None:
    module = import_module("app.main")

    assert module.APP_NAME == "codex-collaboration-coordinator"
    assert module.APP_VERSION == "0.1.0"
    assert module.create_app() is not None
