from __future__ import annotations

from pathlib import Path

import yaml

from app.services.docs_registry_check import build_docs_registry_report


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_registry(tmp_path: Path, documents: list[dict[str, object]]) -> None:
    registry_path = tmp_path / "docs" / "_meta" / "documents.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "metadata_strategy": {
                    "embedded_front_matter": "deferred",
                    "canonical_registry": "docs/_meta/documents.yaml",
                },
                "documents": documents,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_docs_registry_report_passes_when_registry_matches_files(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    _write(tmp_path / "docs" / "README.md")
    _write(tmp_path / "scripts" / "README.md")
    _write_registry(
        tmp_path,
        [
            {"path": "README.md", "source_of_truth": "self", "depends_on": []},
            {"path": "docs/README.md", "source_of_truth": "self", "depends_on": ["README.md"]},
            {"path": "scripts/README.md", "source_of_truth": "self", "depends_on": ["README.md"]},
        ],
    )

    report = build_docs_registry_report(tmp_path)

    assert report.issues == ()
    assert set(report.markdown_paths) == {"README.md", "docs/README.md", "scripts/README.md"}


def test_docs_registry_report_flags_missing_and_stale_entries(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    _write(tmp_path / "docs" / "README.md")
    _write_registry(
        tmp_path,
        [
            {"path": "README.md", "source_of_truth": "self", "depends_on": []},
            {"path": "GHOST.md", "source_of_truth": "self", "depends_on": []},
        ],
    )

    report = build_docs_registry_report(tmp_path)
    issue_codes = {issue.code for issue in report.issues}

    assert "missing_registry_entry" in issue_codes
    assert "stale_registry_entry" in issue_codes


def test_docs_registry_report_flags_broken_metadata_references(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    _write_registry(
        tmp_path,
        [
            {
                "path": "README.md",
                "source_of_truth": "MISSING_SOURCE.md",
                "depends_on": ["MISSING_DEP.md"],
                "supersedes": ["MISSING_OLD.md"],
                "superseded_by": ["MISSING_NEW.md"],
            }
        ],
    )

    report = build_docs_registry_report(tmp_path)
    broken_targets = {issue.message.rsplit(" ", 1)[-1] for issue in report.issues}

    assert broken_targets == {
        "MISSING_DEP.md",
        "MISSING_NEW.md",
        "MISSING_OLD.md",
        "MISSING_SOURCE.md",
    }
