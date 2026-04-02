# Scripts

Local helper scripts:

- `run.ps1` start the app with the `small-team` deployment profile and a non-loopback host; runtime recovery comes from the profile defaults
- `dev.ps1` start the app with the `local-dev` deployment profile and reload enabled
- `seed.ps1` apply migrations and seed demo data, default channels, and planning phase presets
- `smoke.ps1` validate health, readiness, agent card, seed data, phase presets, finalize activation, operator shell anchors/bootstrap, public A2A discovery/task flow, and realtime operator activity while waiting for the app to become ready
- `a2a_quickstart.ps1` run a guided public A2A demo that creates a task, replays events, and prints discovery metadata
- `package_release.ps1` build the curated versioned small-team release bundle and manifest
- `release.ps1` run the release checklist, migration verification, seed reset verification, smoke gate, and release packaging for the `small-team` baseline; it starts a temporary app process for the smoke step when needed and inherits runtime recovery from the profile defaults
- `docs_check.ps1` validate that every tracked Markdown file is covered by `docs/_meta/documents.yaml` and that metadata references do not drift to missing paths
- `test.ps1` run the test suite
- `lint.ps1` run Ruff checks
