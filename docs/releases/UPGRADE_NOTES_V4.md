# Upgrade Notes V4

## What changed

- The coordinator now has a repeatable release checklist.
- Migration application is stricter and fails fast if a previously applied migration file changes.
- Demo seeding is idempotent and can be verified against a fresh SQLite database.
- Release and operational docs are synchronized with the current runtime behavior.

## Upgrade path

1. Pull the latest branch.
2. Recreate your virtual environment if dependencies changed.
3. Keep `DATABASE_URL` pointed at a local SQLite file.
4. Run:

```powershell
.\scripts\release.ps1
```

5. If the release gate reports a migration checksum mismatch, restore the historical migration file and create a new migration instead of editing the old one.

## Safe defaults

- `APP_ENV=development`
- `CODEX_BRIDGE_MODE=local`
- `REQUEST_ID_HEADER=X-Request-ID`
- `DATABASE_URL=sqlite:///./codex_coordinator.db`

These defaults are safe for local work and keep the operator surface consistent with the release checklist.
