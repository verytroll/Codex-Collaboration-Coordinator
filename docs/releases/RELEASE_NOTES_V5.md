# V5 Release Notes

## Release date

2026-04-02

## Baseline

- Package version: `0.2.0`
- Release tag: `v0.2.0`
- Release candidate naming: `v0.2.0-rc.1`
- Packaged small-team bundle: `codex-collaboration-coordinator-0.2.0-small-team`

## Included

- Access boundary and external safety baseline
- Thin operator UI shell
- Realtime operator surface
- A2A interoperability and adoption kit
- Small-team deployment profile and release packaging

## Verification

- `pytest`
- `python -m ruff check app tests`
- `.\scripts\smoke.ps1`
- `.\scripts\release.ps1`

## Operational notes

- `local-dev` remains the everyday developer profile.
- `trusted-demo` remains available for local demo or reverse-proxy validation.
- `small-team` is the packaged baseline profile and is the default release target.
- Release packaging now records the release tag, candidate name, and verification checklist in
  `release-manifest.json`.
