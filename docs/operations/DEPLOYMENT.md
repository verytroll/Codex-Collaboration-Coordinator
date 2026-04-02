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

The packaged `small-team` profile also supplies the durable runtime recovery defaults:

- `RUNTIME_RECOVERY_ENABLED=true`
- `RUNTIME_RECOVERY_INTERVAL_SECONDS=15`
- `RUNTIME_STALE_AFTER_MINUTES=10`
- `OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS=5`
- `OUTBOUND_WEBHOOK_MAX_ATTEMPTS=3`
- `OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS=5`

Keep those variables only when you want to override the packaged profile.

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
- `OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS=5`
- `OUTBOUND_WEBHOOK_MAX_ATTEMPTS=3`
- `OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS=5`
- `LOG_LEVEL=INFO`

Development defaults keep `APP_HOST=127.0.0.1` and `APP_RELOAD=true`.

Access boundary profiles:

- `local` keeps operator/public routes open for local development and tests.
- `trusted` allows local clients without a token and requires a token for non-local access.
- `protected` requires `ACCESS_TOKEN` on operator/public routes for bootstrap and legacy clients, and also accepts managed integration credentials issued by the operator API.

If you enable `protected`, set `ACCESS_TOKEN` and optionally `ACCESS_TOKEN_HEADER`
(`X-Access-Token` by default). That shared token remains the bootstrap path for the
operator shell and smoke scripts.

Managed integration credentials are opaque bearer secrets issued through:

- `POST /api/v1/operator/integration-principals`
- `POST /api/v1/operator/integration-principals/{principal_id}/credentials`

Use `public_read` for read/replay access, `public_write` for public task creation, and
`operator_write` for operator automation. `operator_write` includes the public scopes.
The secret is shown once at issue/rotate time and should be rotated or revoked instead of
being reused indefinitely.
Credential requests accept an explicit empty `scopes: []` when you want no permissions,
and any `expires_at` value must include a timezone offset such as `Z`.

Managed outbound webhooks are configured through operator routes and use the durable runtime
loop for retry/recovery. Tune only these env vars when you need a different delivery
profile:

- `OUTBOUND_WEBHOOK_REQUEST_TIMEOUT_SECONDS`
- `OUTBOUND_WEBHOOK_MAX_ATTEMPTS`
- `OUTBOUND_WEBHOOK_RETRY_BACKOFF_SECONDS`

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
through the profile defaults, so you do not need to set `RUNTIME_RECOVERY_ENABLED=true`
by hand unless you are overriding the packaged path.

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

The current V6 release baseline uses:

- package version `0.3.0`
- release tag `v0.3.0`
- release candidate naming `v0.3.0-rc.1`
- bundle name `codex-collaboration-coordinator-0.3.0-small-team`
- durable runtime recovery enabled through the packaged `small-team` profile defaults

The manifest records the release metadata, baseline package name, profile defaults, and
verification checklist so docs, scripts, and status stay aligned.

For external A2A adoption, treat `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md` as the source of
truth for supported versus experimental surface claims.

For a complete release gate, run `.\scripts\release.ps1`. That script verifies migrations,
seed reset behavior, smoke coverage, and then builds the release bundle.

## Operational assumptions

- The local SQLite file must persist between restarts if you want the state to survive.
- The durable runtime loop is enabled in the packaged `small-team` profile and
  replays queued jobs and outbound webhook deliveries on startup and on a fixed cadence.
- `readinessz` does not replace `system/status`; use both for basic external readiness and
  operator diagnostics.
- Protected operator/public routes return `401` when the token is missing and `403` when
  the token is wrong.
- Managed integration credentials are the preferred path for external clients; the
  shared `ACCESS_TOKEN` remains a bootstrap and legacy fallback.
- Protected write routes return `401` when actor identity headers are missing and `403`
  when the role is not allowed for the requested action.
- External integrators should use the public v1 A2A task and event routes only; the
  legacy adapter bridge remains available for compatibility, not as the supported
  adoption baseline.
- Outbound webhooks reuse the same public task event payload contract; receivers must be
  prepared for `at-least-once` delivery and verify the request signature.
- If you need a new migration, add a new `.sql` file instead of editing an existing one in place.

