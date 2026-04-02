# V6 Release Notes

## Release date

2026-04-02

## Baseline

- Package version: `0.3.0`
- Release tag: `v0.3.0`
- Release candidate naming: `v0.3.0-rc.1`
- Packaged small-team bundle: `codex-collaboration-coordinator-0.3.0-small-team`

## Included

- Operator actions and audit trail
- Identity and team RBAC
- Durable runtime and persistence boundary
- Realtime streaming transport
- Interop certification and external adoption baseline

## Verification

- `pytest`
- `python -m ruff check app tests`
- `.\scripts\smoke.ps1`
- `.\scripts\release.ps1`

## Operational notes

- `small-team` is the packaged baseline profile and is the default release target.
- `local-dev` remains the everyday developer profile.
- `trusted-demo` remains available for local demo or reverse-proxy validation.
- Release packaging records the release tag, candidate name, and verification checklist in
  `release-manifest.json`.
