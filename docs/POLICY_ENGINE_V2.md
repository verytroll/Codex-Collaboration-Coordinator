# Policy Engine V2

`Policy Engine V2` adds scoped automation rules on top of the existing review and approval flows.
It stays in the service layer and writes an audit trail for every policy decision.

## Public API

### Policies

- `GET /api/v1/policies`
- `POST /api/v1/policies`
- `GET /api/v1/policies/{policy_id}`
- `POST /api/v1/policies/{policy_id}/activate`
- `POST /api/v1/policies/{policy_id}/deactivate`
- `POST /api/v1/policies/{policy_id}/pause`
- `POST /api/v1/policies/{policy_id}/resume`
- `GET /api/v1/policies/{policy_id}/decisions`
- `GET /api/v1/policy-decisions`

### Policy fields

- `policy_type`
  - `conditional_auto_approve`
  - `escalation`
  - `template_scoped`
  - `phase_scoped`
- scope fields
  - `session_id`
  - `template_key`
  - `phase_key`
- automation control
  - `is_active`
  - `automation_paused`
  - `pause_reason`
- matching and behavior
  - `conditions`
  - `actions`

## Decision semantics

- `allow`
  - no policy matched, or the matched policy explicitly allowed the gate
- `auto_approve`
  - the approval gate is created, then accepted automatically
- `escalate_review`
  - the approval gate is converted into a review gate
- `paused`
  - automation was paused by operator control
- `resumed`
  - automation was resumed by operator control

## Notes

- Policy decisions are written to `policy_decisions`.
- Session records now keep an internal `template_key` so template-scoped policies can be evaluated.
- The orchestration API does not contain policy logic directly; it delegates to `PolicyEngineV2Service`.
