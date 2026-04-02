# Documentation Index

This repository keeps documentation in three layers:

- root entrypoints: `README.md`, `AGENTS.md`, `scripts/README.md`
- routing docs: `docs/planning/INDEX.md`, `docs/reference/INDEX.md`
- domain docs under the rest of `docs/`

## Recommended Read Order

For most coding tasks:

1. `README.md`
2. `docs/planning/INDEX.md`
3. `docs/planning/STATUS.md`
4. the active phase docs named there
5. `docs/reference/INDEX.md` only if product, contract, schema, or architecture context is needed

Only open `docs/planning/archive/` when the task explicitly depends on historical progression from MVP through V6.

## Tree

```text
docs/
|-- README.md
|-- _meta/
|-- planning/
|   |-- INDEX.md
|   |-- STATUS.md
|   |-- PLAN_V7.md
|   |-- IMPLEMENTATION_TASKS_V7.md
|   |-- IMPLEMENTATION_ORDER_V7.md
|   `-- archive/
|-- reference/
|   |-- INDEX.md
|   |-- PRD.md
|   |-- ARCHITECTURE.md
|   |-- API.md
|   |-- DB_SCHEMA.md
|   `-- BORROWED_IDEAS.md
|-- operations/
|-- operator/
|-- integrations/
|-- releases/
`-- features/
```

## Domains

- `docs/planning/`: active project status and the active implementation phase
- `docs/planning/archive/`: historical plans, backlogs, and implementation orders
- `docs/reference/`: PRD, architecture, API, schema, and strategy references
- `docs/operations/`: deployment, local setup, observability, runbook, troubleshooting
- `docs/operator/`: operator-facing UI and dashboard notes
- `docs/integrations/a2a/`: A2A/public API, events, quickstart, compatibility, mapping
- `docs/features/`: narrower capability notes for feature slices and rollout context
- `docs/releases/`: release notes and upgrade notes
- `docs/_meta/`: metadata registry and schema templates for documentation governance

## Metadata Decision

The repo uses the following metadata schema conceptually:

```yaml
---
title:
doc_type:
domain:
version:
status:
owner:
source_of_truth:
depends_on:
  -
last_updated:
supersedes: []
superseded_by: []
---
```

Current decision:

- canonical metadata lives in `docs/_meta/documents.yaml`
- the reusable schema lives in `docs/_meta/frontmatter.template.yaml`
- embedded front matter is deferred until a docs pipeline consumes it
- every tracked Markdown file must have a registry entry

## Rollout Rule

For now:

- add or update the metadata registry when a doc is created, moved, deprecated, or replaced
- keep repo entrypoint docs at root
- keep active planning docs in `docs/planning/`
- keep historical planning docs in `docs/planning/archive/`
- only add embedded front matter to a specific file if tooling requires file-level metadata
