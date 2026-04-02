# Upgrade Notes V6

## What changed

- The coordinator now has a versioned V6 release baseline.
- The canonical package version is `0.3.0`.
- Release packaging now records release tag and candidate metadata in the manifest.
- The release checklist is synchronized across `README.md`, deployment docs, runbook, and
  the release scripts.

## Upgrade path

1. Pull the latest branch.
2. Keep `DATABASE_URL` pointed at a local SQLite file unless you are explicitly testing
   another profile.
3. Re-run the release gate:

```powershell
.\scripts\release.ps1
```

4. If you consume packaged releases externally, update references to the new bundle name:
   `codex-collaboration-coordinator-0.3.0-small-team`.
5. No schema migration is required just to adopt the release baseline updates.

## Safe defaults

- `APP_ENV=production`
- `DEPLOYMENT_PROFILE=small-team`
- `ACCESS_BOUNDARY_MODE=trusted`
- `DATABASE_URL=sqlite:///./data/codex_coordinator.db`

These defaults match the packaged small-team release baseline and keep the deployment path
aligned with the release manifest.
