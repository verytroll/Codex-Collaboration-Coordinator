# Scripts

Local helper scripts:

- `run.ps1` start the app with the deployment defaults and a non-loopback host
- `dev.ps1` start the app with the development defaults and reload enabled
- `seed.ps1` apply migrations and seed demo data, default channels, and planning phase presets
- `smoke.ps1` validate health, readiness, agent card, seed data, phase presets, finalize activation, operator shell anchors/bootstrap, and basic A2A projection while waiting for the app to become ready
- `a2a_quickstart.ps1` run a guided public A2A demo that creates a task, replays events, and prints discovery metadata
- `release.ps1` run the release checklist, migration verification, seed reset verification, and smoke gate
- `test.ps1` run the test suite
- `lint.ps1` run Ruff checks
