# V7 Release Notes

## Release date

2026-04-02

## Baseline

- Package version: `0.4.0`
- Release tag: `v0.4.0`
- Release candidate naming: `v0.4.0-rc.1`
- Packaged small-team bundle: `codex-collaboration-coordinator-0.4.0-small-team`

## Included

- Team deployment ergonomics and upgrade path
- Operator console polish and incident workflow
- Integration credentials and access lifecycle
- Managed outbound webhook automation for public A2A task events
- Contract governance and early-adopter conformance for the supported public A2A surface

## Verification

- `pytest`
- `python -m ruff check app tests`
- `.\scripts\smoke.ps1`
- `.\scripts\a2a_conformance.ps1`
- `.\scripts\release.ps1`

## Operational notes

- `small-team` remains the packaged baseline profile and the default release target.
- `local-dev` remains the everyday developer profile.
- `trusted-demo` remains available for local demo or reverse-proxy validation.
- Managed integration credentials are the preferred external auth path; the shared access token remains a bootstrap and legacy fallback.
- Managed outbound webhooks are part of the supported early-adopter handoff baseline and inherit durable retry/recovery semantics from the runtime loop.
- Release packaging records the release tag, candidate name, deployment profile, and verification checklist in `release-manifest.json`.
