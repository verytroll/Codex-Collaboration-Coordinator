# API.md

# Đặc tả API: Codex Collaboration Coordinator

## 0. TL;DR (đọc trước để tiết kiệm context)

Khi nào cần mở doc này:

- bạn đang thêm/sửa endpoint, payload, status code, streaming behavior
- bạn cần biết “luồng người dùng” (tạo session → add participants → gửi message → theo dõi job → lấy artifacts)

Các quy ước quan trọng:

- base prefix: `/api/v1/...`, JSON, `snake_case`
- mention format: `#<name>` (resolve theo `display_name` → `role` → `id`)
- command format: message bắt đầu bằng `/new`, `/interrupt`, `/compact`, `/review`
- approvals: job có thể chuyển `auth_required` và cần accept/decline (public) hoặc approve/reject (operator)
- streaming: SSE cho session/job streams và operator activity streams

Nếu bạn chỉ cần “chạy local và nhìn operator UI”, mở `docs/operations/LOCAL_SETUP.md` + `docs/operator/OPERATOR_UI.md` là đủ.

## 1. Mục tiêu của tài liệu

Tài liệu này định nghĩa API cho hệ thống **Codex Collaboration Coordinator** theo hướng:

- **MVP local-first**
- **Coordinator-first**
- **Codex là execution engine phía sau**
- có thể mở rộng dần sang **A2A-compatible API** trong giai đoạn sau

API trong tài liệu này chia thành 2 lớp:

1. **Coordinator API (MVP)**
   - API nội bộ/chính cho session, agent, message, command, artifact
   - dùng cho CLI, Web UI, script local và backend orchestration

2. **A2A-Compatible API (Phase sau)**
   - lớp mở rộng để expose task/message/artifact theo A2A
   - chưa bắt buộc ở MVP, nhưng thiết kế response sẽ chừa đường để map sang A2A dễ dàng

---

## 2. Nguyên tắc thiết kế API

### 2.1 Nguyên tắc chung

- JSON cho request/response
- UTF-8 cho mọi text
- `snake_case` cho field names
- API version đặt ở prefix: `/api/v1/...`
- mọi object chính đều có `id`, `created_at`, `updated_at`
- mọi mutation quan trọng đều ghi event vào state store

### 2.2 Trạng thái HTTP

- `200 OK` — truy vấn hoặc thao tác thành công
- `201 Created` — tạo resource mới thành công
- `202 Accepted` — request đã nhận và đang xử lý async
- `400 Bad Request` — payload sai hoặc thiếu field
- `404 Not Found` — không tìm thấy resource
- `409 Conflict` — trạng thái hiện tại không cho phép thao tác
- `422 Unprocessable Entity` — dữ liệu hợp lệ về format nhưng không hợp lệ về nghiệp vụ
- `500 Internal Server Error` — lỗi hệ thống

### 2.3 Mẫu lỗi thống nhất

```json
{
  "error": {
    "code": "session_not_found",
    "message": "Session không tồn tại",
    "details": {
      "session_id": "ses_123"
    }
  }
}
```

---

## 3. Các đối tượng dữ liệu chính

## 3.1 Session

```json
{
  "id": "ses_001",
  "title": "Fix login flow",
  "goal": "Phối hợp planner, builder, reviewer để sửa login flow",
  "status": "active",
  "lead_agent_id": "agt_planner",
  "active_phase_id": null,
  "created_at": "2026-03-31T12:00:00Z",
  "updated_at": "2026-03-31T12:00:00Z"
}
```

### 3.1.1 Session status

- `draft`
- `active`
- `paused`
- `completed`
- `archived`

---

## 3.2 Agent

```json
{
  "id": "agt_builder",
  "display_name": "builder",
  "role": "builder",
  "is_lead": false,
  "runtime_kind": "codex",
  "runtime_id": "rt_codex_builder",
  "presence": "online",
  "capabilities": {
    "can_code": true,
    "can_review": false,
    "can_plan": false
  },
  "created_at": "2026-03-31T12:00:00Z",
  "updated_at": "2026-03-31T12:00:00Z"
}
```

### 3.2.1 Presence

- `online`
- `offline`
- `busy`
- `unknown`

---

## 3.3 Session Participant

```json
{
  "session_id": "ses_001",
  "agent_id": "agt_builder",
  "joined_at": "2026-03-31T12:05:00Z",
  "read_scope": "shared_history",
  "write_scope": "mention_or_direct_assignment"
}
```

---

## 3.4 Message

```json
{
  "id": "msg_001",
  "session_id": "ses_001",
  "sender_type": "user",
  "sender_id": "usr_local",
  "content": "#builder hãy tạo endpoint /login",
  "message_type": "chat",
  "reply_to_message_id": null,
  "mentions": ["agt_builder"],
  "artifacts": [],
  "created_at": "2026-03-31T12:10:00Z"
}
```

### 3.4.1 Sender type

- `user`
- `agent`
- `system`

### 3.4.2 Message type

- `chat`
- `command`
- `relay`
- `status`
- `approval_request`
- `approval_decision`
- `artifact_notice`

---

## 3.5 Job

Job là đơn vị công việc có trạng thái rõ ràng, thường được tạo khi có mention hoặc command giao việc.

```json
{
  "id": "job_001",
  "session_id": "ses_001",
  "assigned_agent_id": "agt_builder",
  "source_message_id": "msg_001",
  "title": "Tạo endpoint /login",
  "status": "running",
  "hop_count": 0,
  "codex_runtime_id": "rt_codex_builder",
  "codex_thread_id": "thr_abc",
  "active_turn_id": "turn_xyz",
  "created_at": "2026-03-31T12:10:01Z",
  "updated_at": "2026-03-31T12:10:20Z"
}
```

### 3.5.1 Job status

- `queued`
- `running`
- `input_required`
- `auth_required`
- `completed`
- `failed`
- `canceled`
- `paused_by_loop_guard`

---

## 3.6 Artifact

```json
{
  "id": "art_001",
  "job_id": "job_001",
  "session_id": "ses_001",
  "artifact_type": "final_text",
  "title": "Builder summary",
  "content_text": "Đã tạo endpoint /login và test cơ bản.",
  "file_path": null,
  "mime_type": null,
  "created_at": "2026-03-31T12:12:00Z"
}
```

### 3.6.1 Artifact type

- `final_text`
- `diff`
- `file`
- `json`
- `log_excerpt`

---

## 3.7 Approval Request

```json
{
  "id": "apr_001",
  "job_id": "job_001",
  "agent_id": "agt_builder",
  "approval_type": "command_execution",
  "status": "pending",
  "payload": {
    "command": "pytest -q",
    "cwd": "/workspace/project"
  },
  "created_at": "2026-03-31T12:11:00Z",
  "updated_at": "2026-03-31T12:11:00Z"
}
```

### 3.7.1 Approval type

- `command_execution`
- `file_change`
- `network_access`
- `custom`

### 3.7.2 Approval status

- `pending`
- `accepted`
- `declined`
- `canceled`

---

## 4. Coordinator API (MVP)

## 4.1 Health và system

### GET `/api/v1/healthz`

Kiểm tra API server có hoạt động hay không.

**Response**

```json
{
  "status": "ok"
}
```

### GET `/api/v1/system/status`

Trả về trạng thái tổng quan của coordinator.

**Response**

```json
{
  "status": "ok",
  "db": "ok",
  "codex_bridge": "ok",
  "active_sessions": 2,
  "registered_agents": 3,
  "timestamp": "2026-03-31T12:00:00Z"
}
```

---

## 4.2 Session API

### POST `/api/v1/sessions`

Tạo session mới.

**Request**

```json
{
  "title": "Fix login flow",
  "goal": "Planner, builder và reviewer phối hợp sửa login flow",
  "lead_agent_id": "agt_planner"
}
```

**Response** — `201 Created`

```json
{
  "session": {
    "id": "ses_001",
    "title": "Fix login flow",
    "goal": "Planner, builder và reviewer phối hợp sửa login flow",
    "status": "active",
    "lead_agent_id": "agt_planner",
    "active_phase_id": null,
    "created_at": "2026-03-31T12:00:00Z",
    "updated_at": "2026-03-31T12:00:00Z"
  }
}
```

### GET `/api/v1/sessions`

Liệt kê session.

**Response**

```json
{
  "sessions": [
    {
      "id": "ses_001",
      "title": "Fix login flow",
      "goal": "Planner, builder và reviewer phối hợp sửa login flow",
      "status": "active",
      "lead_agent_id": "agt_planner",
      "active_phase_id": null,
      "created_at": "2026-03-31T12:00:00Z",
      "updated_at": "2026-03-31T12:00:00Z"
    }
  ]
}
```

### GET `/api/v1/sessions/{session_id}`

Lấy chi tiết session.

### PATCH `/api/v1/sessions/{session_id}`

Cập nhật metadata session.

**Request**

```json
{
  "title": "Fix login flow v2",
  "goal": "Hoàn tất login flow và review diff"
}
```

### POST `/api/v1/sessions/{session_id}/archive`

Đưa session sang trạng thái `archived`.

### POST `/api/v1/sessions/{session_id}/pause`

Đưa session sang trạng thái `paused`.

### POST `/api/v1/sessions/{session_id}/resume`

Khôi phục session đang `paused` về `active`.

---

## 4.3 Session Participant API

### POST `/api/v1/sessions/{session_id}/participants`

Thêm agent vào session.

**Request**

```json
{
  "agent_id": "agt_builder"
}
```

**Response**

```json
{
  "participant": {
    "session_id": "ses_001",
    "agent_id": "agt_builder",
    "joined_at": "2026-03-31T12:05:00Z",
    "read_scope": "shared_history",
    "write_scope": "mention_or_direct_assignment"
  }
}
```

### GET `/api/v1/sessions/{session_id}/participants`

Liệt kê agents trong session.

### DELETE `/api/v1/sessions/{session_id}/participants/{agent_id}`

Rời hoặc loại agent khỏi session.

---

## 4.4 Agent Registry API

### POST `/api/v1/agents`

Đăng ký một agent.

**Request**

```json
{
  "display_name": "builder",
  "role": "builder",
  "is_lead": false,
  "runtime_kind": "codex",
  "runtime_config": {
    "workspace_path": "/workspace/project",
    "personality": "builder",
    "sandbox_mode": "workspace-write"
  }
}
```

**Response**

```json
{
  "agent": {
    "id": "agt_builder",
    "display_name": "builder",
    "role": "builder",
    "is_lead": false,
    "runtime_kind": "codex",
    "runtime_id": "rt_codex_builder",
    "presence": "unknown",
    "capabilities": {
      "can_code": true,
      "can_review": false,
      "can_plan": false
    },
    "created_at": "2026-03-31T12:00:00Z",
    "updated_at": "2026-03-31T12:00:00Z"
  }
}
```

### GET `/api/v1/agents`

Liệt kê agents đã đăng ký.

### GET `/api/v1/agents/{agent_id}`

Lấy chi tiết agent.

### PATCH `/api/v1/agents/{agent_id}`

Cập nhật metadata agent.

**Request**

```json
{
  "display_name": "builder-1",
  "role": "builder",
  "is_lead": false
}
```

### POST `/api/v1/agents/{agent_id}/heartbeat`

Cập nhật trạng thái sống của agent.

**Request**

```json
{
  "status": "online"
}
```

---

## 4.5 Message API

### POST `/api/v1/sessions/{session_id}/messages`

Gửi message mới vào session.

**Mục đích**
- user chat thường
- mention agent bằng `#agent`
- command text như `/interrupt`
- system hoặc UI gửi message vào session

**Request**

```json
{
  "sender_type": "user",
  "sender_id": "usr_local",
  "content": "#builder hãy tạo endpoint /login",
  "reply_to_message_id": null
}
```

**Response** — `202 Accepted`

```json
{
  "message": {
    "id": "msg_001",
    "session_id": "ses_001",
    "sender_type": "user",
    "sender_id": "usr_local",
    "content": "#builder hãy tạo endpoint /login",
    "message_type": "chat",
    "reply_to_message_id": null,
    "mentions": ["agt_builder"],
    "artifacts": [],
    "created_at": "2026-03-31T12:10:00Z"
  },
  "routing": {
    "detected_mentions": ["agt_builder"],
    "created_jobs": ["job_001"]
  }
}
```

### GET `/api/v1/sessions/{session_id}/messages`

Liệt kê messages trong session.

**Query params**
- `limit` — mặc định 50
- `before` — message id hoặc timestamp
- `after` — message id hoặc timestamp

### GET `/api/v1/messages/{message_id}`

Lấy chi tiết một message.

---

## 4.6 Command API

Command API tách riêng để UI/CLI không cần nhúng command dưới dạng text nếu không muốn.

### POST `/api/v1/sessions/{session_id}/commands/new`

Tạo một lượt làm việc mới cho agent hoặc reset hướng làm việc.

**Request**

```json
{
  "target_agent_id": "agt_builder",
  "instruction": "Bắt đầu task mới: tạo endpoint /login"
}
```

### POST `/api/v1/sessions/{session_id}/commands/interrupt`

Interrupt agent hoặc job đang chạy.

**Request**

```json
{
  "target_agent_id": "agt_builder",
  "job_id": "job_001",
  "reason": "Dừng lại để đổi hướng"
}
```

### POST `/api/v1/sessions/{session_id}/commands/compact`

Yêu cầu compact thread của agent.

**Request**

```json
{
  "target_agent_id": "agt_builder",
  "reason": "Rút gọn lịch sử để tiếp tục phiên dài"
}
```

### POST `/api/v1/sessions/{session_id}/commands/relay`

Relay output từ agent này sang agent khác.

**Request**

```json
{
  "source_agent_id": "agt_planner",
  "target_agent_id": "agt_builder",
  "source_message_id": "msg_010",
  "instruction": "Dựa trên phân tích ở trên, hãy triển khai patch"
}
```

---

## 4.7 Job API

### GET `/api/v1/jobs`

Liệt kê jobs.

**Query params**
- `session_id`
- `assigned_agent_id`
- `status`

### GET `/api/v1/jobs/{job_id}`

Lấy chi tiết job.

### POST `/api/v1/jobs`

Tạo job trực tiếp mà không đi qua parsing message.

**Request**

```json
{
  "session_id": "ses_001",
  "assigned_agent_id": "agt_builder",
  "title": "Tạo endpoint /login",
  "instruction": "Hãy tạo endpoint /login bằng FastAPI"
}
```

### POST `/api/v1/jobs/{job_id}/cancel`

Hủy job đang chạy.

### POST `/api/v1/jobs/{job_id}/retry`

Chạy lại job đã failed hoặc canceled.

### POST `/api/v1/jobs/{job_id}/resume`

Tiếp tục job ở trạng thái `paused_by_loop_guard`, `input_required`, hoặc `auth_required`.

### GET `/api/v1/jobs/{job_id}/events`

Lấy event timeline của job.

**Response**

```json
{
  "events": [
    {
      "id": "evt_001",
      "job_id": "job_001",
      "event_type": "job_started",
      "payload": {},
      "created_at": "2026-03-31T12:10:01Z"
    },
    {
      "id": "evt_002",
      "job_id": "job_001",
      "event_type": "artifact_created",
      "payload": {
        "artifact_id": "art_001"
      },
      "created_at": "2026-03-31T12:12:00Z"
    }
  ]
}
```

---

## 4.8 Approval API

### GET `/api/v1/jobs/{job_id}/approvals`

Liệt kê approval requests của job.

### POST `/api/v1/approvals/{approval_id}/accept`

Chấp thuận approval.

**Request**

```json
{
  "actor_id": "usr_local",
  "note": "Cho phép chạy test"
}
```

### POST `/api/v1/approvals/{approval_id}/decline`

Từ chối approval.

**Request**

```json
{
  "actor_id": "usr_local",
  "note": "Chưa cho phép sửa file ngoài workspace"
}
```

### POST `/api/v1/jobs/{job_id}/input`

Trả lời câu hỏi khi job ở trạng thái `input_required`.

**Request**

```json
{
  "actor_id": "usr_local",
  "content": "Dùng FastAPI và lưu trong apps/api/main.py"
}
```

---

## 4.9 Artifact API

### GET `/api/v1/jobs/{job_id}/artifacts`

Liệt kê artifact của job.

### GET `/api/v1/artifacts/{artifact_id}`

Lấy chi tiết artifact.

### GET `/api/v1/artifacts/{artifact_id}/download`

Tải file artifact nếu artifact là file.

### GET `/api/v1/sessions/{session_id}/artifacts`

Liệt kê artifact toàn session.

---

## 4.10 Presence API

### GET `/api/v1/presence`

Lấy trạng thái presence của toàn bộ agent.

### GET `/api/v1/agents/{agent_id}/presence`

Lấy presence của một agent.

---

## 4.11 Streaming API

### GET `/api/v1/sessions/{session_id}/stream`

SSE stream cho session.

**Event types**
- `message.created`
- `job.created`
- `job.updated`
- `job.completed`
- `approval.requested`
- `artifact.created`
- `agent.presence_changed`
- `loop_guard.triggered`

**Ví dụ event**

```text
event: message.created
data: {"id":"msg_001","session_id":"ses_001","content":"#builder hãy tạo endpoint /login"}
```

### GET `/api/v1/jobs/{job_id}/stream`

SSE stream riêng cho một job.

**Event types**
- `job.updated`
- `codex.output.delta`
- `artifact.created`
- `approval.requested`
- `job.completed`

---

## 5. Quy tắc routing cho message

## 5.1 Message thường

Nếu message không chứa mention và không phải command:
- lưu như `message_type = chat`
- broadcast vào session
- không tạo job

## 5.2 Message có mention `#agent`

Nếu message chứa `#agent_name`:
- parse ra agent đích
- kiểm tra agent có trong session không
- tạo job mới
- tạo relay prompt cho agent
- gắn message gốc vào `source_message_id`

## 5.3 Command text

Nếu message bắt đầu bằng `/`:
- parse như command
- validate quyền của sender
- chuyển sang command handler

Ví dụ:
- `/interrupt #builder`
- `/compact #reviewer`
- `/new #planner Hãy chia task thành 3 bước`

---

## 6. Quy tắc quyền hạn cơ bản

## 6.1 Lead permissions

Lead có thể:
- relay giữa các agent
- interrupt bất kỳ agent nào trong session
- compact bất kỳ thread nào trong session
- pause/resume session

## 6.2 Non-lead permissions

Non-lead có thể:
- gửi chat thường
- mention để đề xuất trao đổi
- trả lời job nếu bị assign trực tiếp

Non-lead không nên tự động điều phối relay đa bước nếu policy chưa cho phép.

## 6.3 System actions

System có thể:
- trigger loop guard
- đánh dấu offline
- queue message cho agent offline
- publish status event

---

## 7. Loop guard API behavior

Khi số hop relay vượt ngưỡng cấu hình:
- job hoặc session bị đánh dấu `paused_by_loop_guard`
- phát event `loop_guard.triggered`
- từ chối relay mới cho đến khi được resume

**Ví dụ response khi bị block:**

```json
{
  "error": {
    "code": "loop_guard_triggered",
    "message": "Relay loop đã vượt ngưỡng cho phép và đang bị tạm dừng",
    "details": {
      "session_id": "ses_001",
      "job_id": "job_014",
      "hop_count": 9,
      "hop_limit": 8
    }
  }
}
```

---

## 8. Mapping sang CodexBridge

Coordinator API không lộ trực tiếp primitive của Codex, nhưng bên trong sẽ map như sau:

- tạo job mới → `thread/start` nếu agent chưa có thread trong session
- bắt đầu xử lý job → `turn/start`
- đổi hướng trong lúc đang chạy → `turn/steer`
- hủy job → `turn/interrupt`
- compact thread → `thread/compact/start`
- khôi phục context sau restart → `thread/resume` nếu khả dụng

---

## 9. A2A-Compatible API (Phase sau)

Phần này chưa bắt buộc cho MVP, nhưng nên được reserve ngay từ bây giờ.

## 9.1 Agent Card

### GET `/.well-known/agent-card.json`

Mô tả agent/coordinator theo chuẩn discovery.

**MVP định hướng**
- `streaming = true`
- `push_notifications = false`
- mô tả skill collaboration + codex execution

## 9.2 Task endpoints dự kiến

### POST `/a2a/message:send`
- map từ create job hoặc send message vào coordinator

### POST `/a2a/message:stream`
- map sang session/job SSE stream

### GET `/a2a/tasks/{task_id}`
- map từ `job_id`

### POST `/a2a/tasks/{task_id}:cancel`
- map sang cancel job

### POST `/a2a/tasks/{task_id}:subscribe`
- map sang stream job updates

## 9.3 Mapping A2A task status

- `submitted` → `queued`
- `working` → `running`
- `input_required` → `input_required`
- `auth_required` → `auth_required`
- `completed` → `completed`
- `canceled` → `canceled`
- `failed` → `failed`

---

## 10. Trình tự gọi API đề xuất cho MVP

## 10.1 Luồng đơn giản: tạo session và giao việc cho builder

1. `POST /api/v1/agents` để đăng ký `planner`, `builder`, `reviewer`
2. `POST /api/v1/sessions` để tạo session
3. `POST /api/v1/sessions/{session_id}/participants` để thêm các agent vào session
4. `POST /api/v1/sessions/{session_id}/messages` với nội dung `#builder hãy tạo endpoint /login`
5. `GET /api/v1/jobs/{job_id}` để theo dõi trạng thái
6. `GET /api/v1/jobs/{job_id}/artifacts` để lấy kết quả

## 10.2 Luồng có approval

1. User giao job cho builder
2. Job chuyển sang `auth_required`
3. UI gọi `GET /api/v1/jobs/{job_id}/approvals`
4. User chọn approve
5. UI gọi `POST /api/v1/approvals/{approval_id}/accept`
6. Job tiếp tục chạy đến hoàn tất

## 10.3 Luồng có relay nhiều agent

1. User gửi `#planner phân tích bug login`
2. Planner trả summary
3. Lead hoặc system tạo relay sang builder bằng `POST /api/v1/sessions/{session_id}/commands/relay`
4. Builder sinh patch
5. Lead relay diff sang reviewer
6. Reviewer trả kết luận vào session

---

## 11. API ưu tiên cho bản đầu

Để tránh quá tải, MVP chỉ cần ưu tiên triển khai trước các endpoint sau:

### Nhóm A — Bắt buộc
- `GET /api/v1/healthz`
- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/agents`
- `POST /api/v1/sessions/{session_id}/participants`
- `POST /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/artifacts`
- `GET /api/v1/sessions/{session_id}/stream`

### Nhóm B — Cần sớm có
- `POST /api/v1/sessions/{session_id}/commands/interrupt`
- `POST /api/v1/sessions/{session_id}/commands/compact`
- `GET /api/v1/jobs/{job_id}/approvals`
- `POST /api/v1/approvals/{approval_id}/accept`
- `POST /api/v1/approvals/{approval_id}/decline`
- `POST /api/v1/jobs/{job_id}/input`

### Nhóm C — Phase sau
- `POST /api/v1/jobs/{job_id}/retry`
- `POST /api/v1/jobs/{job_id}/resume`
- `GET /.well-known/agent-card.json`
- toàn bộ `/a2a/...`

---

## 12. Ghi chú triển khai

- Bản đầu nên giữ API **đơn giản và rõ nghĩa**, không tối ưu hóa quá sớm.
- Không cần public internet ngay; local-first là đủ.
- Nên viết test cho từng endpoint trước khi gắn CodexBridge thật.
- Có thể fake CodexBridge ở test để kiểm tra router, relay, job state và streaming.
- Khi mở rộng sang A2A, nên thêm lớp adapter riêng thay vì trộn vào Coordinator API ngay từ đầu.

