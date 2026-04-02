# Session Templates

Session templates define repeatable collaboration presets for session creation.

## Contract

Each template carries:

- `template_key`
- `title`
- `default_goal`
- `participant_roles`
- `channels`
- `phase_order`
- `rule_presets`
- `orchestration.default_active_phase_key`

## Endpoints

- `GET /api/v1/session-templates`
- `POST /api/v1/session-templates`
- `GET /api/v1/session-templates/{template_key}`
- `POST /api/v1/session-templates/{template_key}/instantiate`

## Built-in templates

The service ships with four presets:

- `planning_heavy`
- `implementation_review`
- `research_review`
- `hotfix_triage`

## Instantiate behavior

When a session is instantiated from a template:

- default channels are still available
- template-defined channels are added or override defaults by key
- phase presets are seeded in template order, then missing default phases are appended
- rule presets are created through the rules service
- the active phase is taken from `orchestration.default_active_phase_key` when present

## Notes

- Template creation is stored in SQLite.
- Built-in templates are reserved keys and cannot be overwritten through the create API.
- The session create API remains unchanged for direct session creation.
