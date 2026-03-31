"""Structured relay template helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RelayTemplateDefinition:
    """Metadata for a structured relay template."""

    template_key: str
    title: str
    source_role: str
    target_role: str
    description: str
    default_channel_key: str
    section_keys: tuple[str, ...]


class RelayTemplatesService:
    """Build and render structured relay templates."""

    _DEFINITIONS: tuple[RelayTemplateDefinition, ...] = (
        RelayTemplateDefinition(
            template_key="planner_to_builder",
            title="Planner to Builder",
            source_role="planner",
            target_role="builder",
            description="Scoped implementation handoff from planner to builder.",
            default_channel_key="planning",
            section_keys=("objective", "scope", "acceptance_criteria", "constraints", "notes"),
        ),
        RelayTemplateDefinition(
            template_key="builder_to_reviewer",
            title="Builder to Reviewer",
            source_role="builder",
            target_role="reviewer",
            description="Structured handoff for review of builder output.",
            default_channel_key="review",
            section_keys=(
                "completed_work",
                "files_changed",
                "tests_run",
                "open_questions",
                "review_focus",
            ),
        ),
        RelayTemplateDefinition(
            template_key="reviewer_to_builder_revise",
            title="Reviewer to Builder Revise",
            source_role="reviewer",
            target_role="builder",
            description="Review decision translated into a revise request.",
            default_channel_key="review",
            section_keys=(
                "decision",
                "summary",
                "required_changes",
                "revision_priority",
                "next_actions",
            ),
        ),
    )

    def list_templates(self) -> list[RelayTemplateDefinition]:
        """Return the available structured relay templates."""
        return list(self._DEFINITIONS)

    def get_template(self, template_key: str) -> RelayTemplateDefinition:
        """Return a template definition by key."""
        for definition in self._DEFINITIONS:
            if definition.template_key == template_key:
                return definition
        raise LookupError(f"Unknown relay template: {template_key}")

    def build_planner_to_builder(
        self,
        *,
        objective: str,
        scope: str | None = None,
        acceptance_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Build a planner-to-builder handoff payload."""
        return self._build_payload(
            template_key="planner_to_builder",
            sections={
                "objective": objective,
                "scope": scope,
                "acceptance_criteria": acceptance_criteria or [],
                "constraints": constraints or [],
                "notes": notes,
            },
            metadata={
                "handoff_kind": "planning",
            },
        )

    def build_builder_to_reviewer(
        self,
        *,
        job_id: str,
        job_title: str,
        job_status: str,
        assigned_agent_id: str,
        reviewer_agent_id: str,
        completed_work: str | None,
        files_changed: list[dict[str, Any]],
        tests_run: list[str],
        open_questions: list[str] | None = None,
        review_focus: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Build a builder-to-reviewer review payload."""
        return self._build_payload(
            template_key="builder_to_reviewer",
            sections={
                "completed_work": completed_work,
                "files_changed": files_changed,
                "tests_run": tests_run,
                "open_questions": open_questions or [],
                "review_focus": review_focus,
                "notes": notes,
            },
            metadata={
                "job_id": job_id,
                "job_title": job_title,
                "job_status": job_status,
                "assigned_agent_id": assigned_agent_id,
                "reviewer_agent_id": reviewer_agent_id,
            },
        )

    def build_reviewer_to_builder_revise(
        self,
        *,
        job_id: str,
        job_title: str,
        reviewer_agent_id: str,
        decision: str,
        summary: str | None,
        required_changes: list[str],
        revision_priority: str = "normal",
        next_actions: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Build a reviewer-to-builder revise payload."""
        return self._build_payload(
            template_key="reviewer_to_builder_revise",
            sections={
                "decision": decision,
                "summary": summary,
                "required_changes": required_changes,
                "revision_priority": revision_priority,
                "next_actions": next_actions or [],
                "notes": notes,
            },
            metadata={
                "job_id": job_id,
                "job_title": job_title,
                "reviewer_agent_id": reviewer_agent_id,
            },
        )

    def render_markdown(self, payload: dict[str, Any]) -> str:
        """Render a structured payload into readable markdown."""
        definition = self.get_template(str(payload["template_key"]))
        lines = [
            f"# {definition.title}",
            "",
            f"Template: `{definition.template_key}`",
            f"Source role: `{definition.source_role}`",
            f"Target role: `{definition.target_role}`",
            f"Channel: `{definition.default_channel_key}`",
        ]
        summary = payload.get("summary")
        if isinstance(summary, str) and summary.strip():
            lines.extend(["", summary.strip()])

        sections = payload.get("sections")
        if isinstance(sections, dict):
            for section_key in definition.section_keys:
                if section_key not in sections:
                    continue
                lines.extend(["", f"## {section_key.replace('_', ' ').title()}"])
                lines.extend(self._render_section_value(sections[section_key], indent=0))

        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and metadata:
            lines.extend(["", "## Metadata"])
            lines.extend(self._render_section_value(metadata, indent=0))

        return "\n".join(lines).strip()

    def _build_payload(
        self,
        *,
        template_key: str,
        sections: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        definition = self.get_template(template_key)
        payload: dict[str, Any] = {
            "template_key": definition.template_key,
            "title": definition.title,
            "source_role": definition.source_role,
            "target_role": definition.target_role,
            "channel_key": definition.default_channel_key,
            "summary": definition.description,
            "sections": sections,
            "metadata": metadata,
        }
        return payload

    def _render_section_value(self, value: Any, *, indent: int) -> list[str]:
        prefix = "  " * indent + "- "
        if isinstance(value, dict):
            lines: list[str] = []
            for key, nested_value in value.items():
                lines.append(f"{prefix}{key}:")
                lines.extend(self._render_section_value(nested_value, indent=indent + 1))
            return lines
        if isinstance(value, list):
            lines = []
            if not value:
                lines.append(f"{prefix}(none)")
                return lines
            for item in value:
                lines.extend(self._render_section_value(item, indent=indent))
            return lines
        if value is None:
            return [f"{prefix}(none)"]
        if isinstance(value, str):
            if "\n" in value:
                return [f"{prefix}{line}" for line in value.splitlines()]
            return [f"{prefix}{value}"]
        return [f"{prefix}{json.dumps(value, sort_keys=True)}"]
