# Deployment

## Minimum deployment profile

This project is intentionally conservative for external deployment:

- Python 3.11 runtime
- single FastAPI process
- SQLite on a writable local volume
- CodexBridge running in local mode unless another mode is explicitly configured

The container and script surface are designed for a small deployment profile first, not a
distributed platform.

## Deployment profiles

| Profile | Intended use | Default host | Default reload | Default DB | Default access |
| --- | --- | --- | --- | --- | --- |
| `local-dev` | everyday development | `127.0.0.1` | `true` | `sqlite:///./codex_coordinator.db` | `local` |
| `trusted-demo` | demo or reverse-proxy testing | `127.0.0.1` | `false` | `sqlite:///./codex_coordinator.db` | `trusted` |
| `small-team` | packaged small-team deployment | `0.0.0.0` | `false` | `sqlite:///./data/codex_coordinator.db` | `trusted` |

`DEPLOYMENT_PROFILE` selects one of these profiles. Any explicit environment variable
still wins if you override an individual setting.

## Environment variables

Recommended deployment defaults:

- `APP_ENV=production`
- `DEPLOYMENT_PROFILE=small-team`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `APP_RELOAD=false`
- `DATABASE_URL=sqlite:///./data/codex_coordinator.db`
- `CODEX_BRIDGE_MODE=local`
- `ACCESS_BOUNDARY_MODE=trusted`
- `RUNTIME_RECOVERY_ENABLED=true`
- `RUNTIME_RECOVERY_INTERVAL_SECONDS=15`
- `RUNTIME_STALE_AFTER_MINUTES=10`
- `LOG_LEVEL=INFO`

Development defaults keep `APP_HOST=127.0.0.1` and `APP_RELOAD=true`.

Access boundary profiles:

- `local` keeps operator/public routes open for local development and tests.
- `trusted` allows local clients without a token and requires a token for non-local access.
- `protected` requires `ACCESS_TOKEN` on operator/public routes.

If you enable `protected`, set `ACCESS_TOKEN` and optionally `ACCESS_TOKEN_HEADER`
(`X-Access-Token` by default).

Protected write paths also expect actor identity headers:

- `ACTOR_ID_HEADER` / `X-Actor-Id`
- `ACTOR_ROLE_HEADER` / `X-Actor-Role`
- `ACTOR_TYPE_HEADER` / `X-Actor-Type`
- `ACTOR_LABEL_HEADER` / `X-Actor-Label`

The operator shell injects these headers from the rendered config defaults so the
protected UI flow stays usable without manual header setup. Direct API clients should
send the same headers explicitly.

For durable deployments, the coordinator can also run a background recovery loop that
replays queued jobs after restart. The packaged `small-team` release enables this loop
with `RUNTIME_RECOVERY_ENABLED=true`.

The operator shell lives at `GET /operator` and bootstraps from
`GET /api/v1/operator/shell`. Both routes follow the same access boundary rules as the
rest of the operator/public surface.

## Startup contract

The application startup path applies SQLite migrations before the API is served.

Deployment readiness is split into two probes:

- `GET /api/v1/healthz` for liveness
- `GET /api/v1/readinessz` for database and migration readiness

If `readinessz` returns `503`, check the database URL and the migration state before retrying.

## Container path

Build the default image from the repository root:

```powershell
docker build -t codex-collaboration-coordinator .
```

Run it with a writable SQLite volume:

```powershell
docker run --rm -p 8000:8000 `
  -e DATABASE_URL=sqlite:///./data/codex_coordinator.db `
  -e APP_ENV=production `
  -v ${PWD}\data:/app/data `
  codex-collaboration-coordinator
```

The health check in `Dockerfile` polls `GET /api/v1/readinessz`.

## Release packaging

Run the release packager to build a curated bundle for the `small-team` profile:

```powershell
.\scripts\package_release.ps1
```

The bundle is written to `dist/release/` and includes a profile-specific env file plus
`release-manifest.json` with the canonical deployment defaults.

The current V5 release baseline uses:

- package version `0.2.0`
- release tag `v0.2.0`
- release candidate naming `v0.2.0-rc.1`
- bundle name `codex-collaboration-coordinator-0.2.0-small-team`
- durable runtime recovery enabled through the packaged env file

The manifest records the release metadata, baseline package name, and verification
checklist so docs, scripts, and status stay aligned.

For external A2A adoption, treat `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md` as the source of
truth for supported versus experimental surface claims.

For a complete release gate, run `.\scripts\release.ps1`. That script verifies migrations,
seed reset behavior, smoke coverage, and then builds the release bundle.

## Operational assumptions

- The local SQLite file must persist between restarts if you want the state to survive.
- The durable runtime loop is enabled in the packaged `small-team` profile and
  replays queued jobs on startup and on a fixed cadence.
- `readinessz` does not replace `system/status`; use both for basic external readiness and
  operator diagnostics.
- Protected operator/public routes return `401` when the token is missing and `403` when
  the token is wrong.
- Protected write routes return `401` when actor identity headers are missing and `403`
  when the role is not allowed for the requested action.
- External integrators should use the public v1 A2A task and event routes only; the
  legacy adapter bridge remains available for compatibility, not as the supported
  adoption baseline.
- If you need a new migration, add a new `.sql` file instead of editing an existing one in place.

