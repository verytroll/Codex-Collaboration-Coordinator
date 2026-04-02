# Observability

Tài liệu này mô tả cách đọc các surface telemetry và log correlation trong `Codex Collaboration Coordinator`.

## Log semantics

- Mỗi request đi qua `RequestIdMiddleware` và được gắn `request_id`, `request_method`, `request_path`.
- Các flow nghiệp vụ có thể bám thêm `session_id`, `agent_id`, `job_id`, `phase_id`, `review_id`, `runtime_pool_id`, `runtime_id`, `task_id`, `subscription_id`, `codex_thread_id`, `event_type`.
- Các field này xuất hiện trong formatter log chuẩn, nên có thể grep theo request hoặc theo entity cụ thể để lần ngược flow.

## Telemetry surface

Telemetry được giữ trong bộ nhớ tiến trình hiện tại và trả về qua:

- `GET /api/v1/system/status`
- `GET /api/v1/system/debug`
- `GET /api/v1/operator/dashboard`

Mỗi response có một khối `telemetry` với:

- `sample_counts`: số sample theo loại
- `summary`: metric live/recent được rút ra từ sample mới nhất
- `latest`: sample gần nhất theo loại
- `recent_samples`: timeline gần nhất trong tiến trình hiện tại

## Summary fields

- `queue_depth`: độ đầy hàng đợi hiện tại
- `average_job_latency_seconds`: độ trễ trung bình của job đang chờ/đang chạy
- `average_phase_duration_seconds`: thời gian trung bình của phase active
- `pending_review_bottlenecks`: số review đang chờ
- `degraded_runtime_pools`: danh sách runtime pool không ở trạng thái `ready`
- `runtime_pool_pressure`: chi tiết pressure theo pool key
- `public_task_throughput`: throughput tổng hợp cho public task/event flow
- `bridge.error_rate`: tỷ lệ sample CodexBridge lỗi trên tổng sample bridge

## How to use

- Nếu cần biết request nào tạo log nào, bắt đầu từ `request_id`.
- Nếu cần hiểu hệ thống đang chậm ở đâu, xem `telemetry.summary.queue_depth`, `runtime_pool_pressure`, `pending_review_bottlenecks`, và `public_task_throughput`.
- Nếu cần hiểu bridge có lỗi gần đây không, xem `telemetry.summary.bridge`.
- Nếu cần debug sâu, đối chiếu `latest` và `recent_samples` với `diagnostics` của system/debug/dashboard.
## Streaming traces

- `GET /api/v1/operator/sessions/{session_id}/activity/stream` uses SSE and resumes with `since_sequence` or `Last-Event-ID`.
- `GET /api/v1/a2a/tasks/{task_id}/stream` and `GET /api/v1/a2a/subscriptions/{subscription_id}/events` expose the public task stream with the same resume pattern.
- If a stream reconnects too often, inspect the response status, the `Last-Event-ID` header, and the stream-specific telemetry samples for `operator_session_activity` and `public_event_stream`.
