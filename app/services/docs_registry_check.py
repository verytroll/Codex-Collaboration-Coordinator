"""Validate Markdown documentation coverage against the docs metadata registry."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIR_NAMES = frozenset(
    {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "data",
        "dist",
    }
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single docs registry validation problem."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DocsRegistryReport:
    """Summary of docs registry validation."""

    markdown_paths: tuple[str, ...]
    registry_paths: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]


def _normalize_string_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _load_yaml_module():
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required to validate docs/_meta/documents.yaml.") from exc
    return yaml


def _load_documents(registry_path: Path) -> list[dict[str, object]]:
    yaml = _load_yaml_module()
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Docs registry root must be a YAML mapping.")
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise ValueError("Docs registry must define a top-level documents list.")
    if not all(isinstance(document, dict) for document in documents):
        raise ValueError("Each docs registry entry must be a YAML mapping.")
    return list(documents)


def _collect_markdown_paths(repo_root: Path) -> tuple[str, ...]:
    markdown_paths: list[str] = []
    for path in repo_root.rglob("*.md"):
        relative_path = path.relative_to(repo_root)
        if any(part in IGNORED_DIR_NAMES for part in relative_path.parts):
            continue
        markdown_paths.append(relative_path.as_posix())
    return tuple(sorted(markdown_paths))


def _document_path(document: dict[str, object]) -> str:
    path = document.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Each docs registry entry must define a non-empty path.")
    return _normalize_string_path(path)


def _string_list(document: dict[str, object], field_name: str) -> list[str]:
    values = document.get(field_name, [])
    if values in (None, []):
        return []
    if not isinstance(values, list):
        raise ValueError(f"Field {field_name!r} must be a YAML list.")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"Field {field_name!r} must contain non-empty strings.")
    return [_normalize_string_path(value) for value in values]


def _related_paths(document: dict[str, object]) -> list[str]:
    related_paths: list[str] = []
    source_of_truth = document.get("source_of_truth")
    if isinstance(source_of_truth, str) and source_of_truth.strip() and source_of_truth != "self":
        related_paths.append(_normalize_string_path(source_of_truth))
    related_paths.extend(_string_list(document, "depends_on"))
    related_paths.extend(_string_list(document, "supersedes"))
    related_paths.extend(_string_list(document, "superseded_by"))
    return related_paths


def build_docs_registry_report(
    repo_root: Path,
    registry_path: Path | None = None,
) -> DocsRegistryReport:
    """Build a validation report for the docs metadata registry."""
    normalized_root = repo_root.resolve()
    normalized_registry = registry_path or normalized_root / "docs" / "_meta" / "documents.yaml"
    documents = _load_documents(normalized_registry)
    markdown_paths = _collect_markdown_paths(normalized_root)
    registry_paths = tuple(_document_path(document) for document in documents)
    issues = _validate_registry(normalized_root, documents, markdown_paths, registry_paths)
    return DocsRegistryReport(
        markdown_paths=markdown_paths,
        registry_paths=registry_paths,
        issues=tuple(issues),
    )


def _validate_registry(
    repo_root: Path,
    documents: list[dict[str, object]],
    markdown_paths: tuple[str, ...],
    registry_paths: tuple[str, ...],
) -> list[ValidationIssue]:
    issues = _registry_coverage_issues(markdown_paths, registry_paths)
    for document in documents:
        current_path = _document_path(document)
        for target_path in _related_paths(document):
            if not (repo_root / Path(target_path)).exists():
                issues.append(
                    ValidationIssue(
                        code="broken_reference",
                        message=f"{current_path} references missing path {target_path}",
                    )
                )
    return issues


def _registry_coverage_issues(
    markdown_paths: tuple[str, ...],
    registry_paths: tuple[str, ...],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path, count in sorted(Counter(registry_paths).items()):
        if count > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_registry_entry",
                    message=f"{path} appears {count} times in docs/_meta/documents.yaml",
                )
            )
    markdown_set = set(markdown_paths)
    registry_set = set(registry_paths)
    for path in sorted(markdown_set - registry_set):
        issues.append(
            ValidationIssue(
                code="missing_registry_entry",
                message=f"{path} exists on disk but is missing from docs/_meta/documents.yaml",
            )
        )
    for path in sorted(registry_set - markdown_set):
        issues.append(
            ValidationIssue(
                code="stale_registry_entry",
                message=f"{path} is registered in docs/_meta/documents.yaml but missing on disk",
            )
        )
    return issues


def main(argv: Sequence[str] | None = None) -> int:
    """Validate docs/_meta/documents.yaml against Markdown files in the repo."""
    parser = argparse.ArgumentParser(description="Validate the docs metadata registry.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root to validate",
    )
    parser.add_argument(
        "--registry-path",
        default=None,
        help="Override the docs metadata registry path",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_docs_registry_report(
        repo_root=Path(args.repo_root),
        registry_path=Path(args.registry_path) if args.registry_path else None,
    )
    if report.issues:
        print("Docs registry validation failed:")
        for issue in report.issues:
            print(f"- [{issue.code}] {issue.message}")
        return 1
    print(
        "Docs registry validation passed: "
        f"{len(report.markdown_paths)} markdown files matched "
        f"{len(report.registry_paths)} registry entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
