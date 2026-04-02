# Upgrade Notes V7

## What changed

- The coordinator now has a versioned V7 release baseline.
- The canonical package version is `0.4.0`.
- The packaged `small-team` release baseline now includes the V7 operator workflow, managed integration credentials, outbound webhook delivery, and the A2A conformance verifier.
- Release packaging now records the V7 baseline metadata and handoff checklist in the manifest.

## Upgrade path

1. Pull the latest branch.
2. Keep `DATABASE_URL` pointed at a writable SQLite file unless you are explicitly testing another profile.
3. Re-run the release gate:

```powershell
.\scripts\release.ps1
```

4. If you consume packaged releases externally, update references to the new bundle name:
   `codex-collaboration-coordinator-0.4.0-small-team`.
5. If your external clients still rely on the bootstrap shared token, keep that path only for operator bootstrap or legacy flows and move supported integrations to managed credentials.
6. If you adopt outbound webhooks, persist the signing secret at issue time and treat delivery as `at-least-once` with idempotent receivers.
7. No schema migration requires manual intervention beyond the normal app startup migration path for this baseline.

## Safe defaults

- `APP_ENV=production`
- `DEPLOYMENT_PROFILE=small-team`
- `ACCESS_BOUNDARY_MODE=trusted`
- `DATABASE_URL=sqlite:///./data/codex_coordinator.db`

These defaults match the packaged small-team V7 release baseline and keep the deployment path aligned with the release manifest and early-adopter handoff checks.
