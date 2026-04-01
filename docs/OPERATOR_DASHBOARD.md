# Operator Dashboard

`F30` adds an operator-facing surface under `/api/v1/operator` for aggregate debugging and queue inspection.

## Endpoints

- `GET /api/v1/operator/dashboard`
- `GET /api/v1/operator/debug`

## Shared Filters

Both endpoints accept these query params:

- `session_id`
- `template_key`
- `phase_key`
- `runtime_pool_key`

The filters are normalized in the response payload under `filters`.

## Dashboard Payload

`/dashboard` returns:

- `queue_heat`
- `phase_distribution`
- `review_bottlenecks`
- `runtime_pools`
- `public_task_throughput`
- `bottlenecks`
- `diagnostics`

The surface is built from repository/service aggregates, not inline SQL inside the route layer.

## Debug Payload

`/debug` returns:

- `dashboard`
- `debug`

`debug` is the legacy compact operator debug surface from `/api/v1/system/debug`. The new dashboard summary is included alongside it so operators can inspect bottlenecks and still keep the existing compact details.

## Notes

- `template_key` applies to template-bearing records such as reviews and public tasks.
- `runtime_pool_key` drives pool health and queue heat filtering.
- The surface is intended to be stable enough for a future UI, but still lightweight for CLI/operator use.
