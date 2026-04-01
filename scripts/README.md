# Scripts

Local helper scripts:

- `run.ps1` start the app with uvicorn
- `dev.ps1` start the app with the development defaults
- `seed.ps1` apply migrations and seed demo data, default channels, and planning phase presets
- `smoke.ps1` validate health, agent card, seed data, phase presets, finalize activation, and basic A2A projection while waiting for the app to become ready
- `release.ps1` run the release checklist, migration verification, seed reset verification, and smoke gate
- `test.ps1` run the test suite
- `lint.ps1` run Ruff checks
