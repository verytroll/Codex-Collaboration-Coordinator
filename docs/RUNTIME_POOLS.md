# Runtime Pools and Work Contexts

F29 adds a public surface for runtime pool assignment and isolated work contexts.

## Concepts

- `runtime_pools` describe how jobs are grouped for execution.
- `work_contexts` bind a job to a pool, runtime, workspace path, and ownership state.
- Built-in pools are available by default:
  - `general_shared`
  - `isolated_work`

## Public API

- `GET /api/v1/runtime-pools`
- `POST /api/v1/runtime-pools`
- `GET /api/v1/runtime-pools/{pool_key}`
- `GET /api/v1/runtime-pools/diagnostics`
- `POST /api/v1/runtime-pools/{pool_key}/assign`
- `GET /api/v1/work-contexts`
- `GET /api/v1/work-contexts/{context_id}`
- `POST /api/v1/work-contexts/{context_id}/recover`

## Assignment Rules

- Jobs may request a preferred runtime pool through `preferred_runtime_pool_key`.
- Jobs may also declare required capabilities through `required_capabilities`.
- The coordinator prefers the requested pool, then falls back to the pool's fallback, then the default pool.
- If a pool is at capacity, the assignment falls back before creating a new active context.
- If a runtime is not currently available, the work context is recorded as `waiting_for_runtime` and can later be recovered.

## Diagnostics

- Pool diagnostics report:
  - active context count
  - waiting context count
  - borrowed context count
  - available runtime count
  - utilization ratio
- Work context responses expose:
  - pool key
  - runtime binding
  - workspace path
  - context status
  - ownership state

