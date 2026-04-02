# V3 Release Notes

## Release date

2026-04-01

## Scope

This release hardens the coordinator for release readiness and operational safety.

Included:

- repeatable local release checklist
- migration checksum validation
- demo seed reset verification
- smoke gate standardization
- runbook and troubleshooting updates

## Validation

- `pytest`
- `ruff check .`
- `ruff format --check .`
- `.\scripts\release.ps1`

## Operational notes

- Existing SQLite databases stay compatible unless a migration checksum mismatch is detected.
- If a checksum mismatch occurs, rebuild the local database from the current migrations instead of editing historical migrations in place.
- `.\scripts\smoke.ps1` is still the quickest way to validate a running local server.
