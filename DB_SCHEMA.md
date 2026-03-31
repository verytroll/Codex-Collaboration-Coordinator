# DB_SCHEMA.md

# Thiết kế cơ sở dữ liệu: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chốt thiết kế cơ sở dữ liệu cho **Codex Collaboration Coordinator** theo hướng:

- **MVP local-first**
- **Coordinator-first**
- **Codex là execution engine phía sau**
- **state được lưu bền để có thể restart/recover**
- có thể mở rộng dần sang **A2A-compatible API** về sau

Schema này được thiết kế để khớp với các tài liệu đã có:
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`

Trọng tâm của schema là lưu bền các thực thể sau:
- `session`
- `agent`
- `session participant`
- `message`
- `job`
- `artifact`
- `approval`
- `codex runtime/thread/turn mapping`
- `presence/heartbeat`
- `relay history`

---

## 2. Nguyên tắc thiết kế

### 2.1 Nguyên tắc chung

- Ưu tiên **đơn giản, rõ ràng, dễ debug** cho MVP
- Dùng **UUID/string id** ở tầng ứng dụng thay vì phụ thuộc vào auto-increment để dễ sync/log
- Mọi bảng chính đều có:
  - `id`
  - `created_at`
  - `updated_at`
- Các trạng thái nghiệp vụ được lưu bằng **TEXT + CHECK constraint** ở MVP
- Không lưu logic vào DB quá sớm; logic chính nằm ở coordinator/service layer
- Ưu tiên lưu **event/audit trail đủ dùng** để điều tra khi hệ thống relay sai

### 2.2 DB engine đề xuất

**MVP:** SQLite
- dễ chạy local
- setup đơn giản
- phù hợp phát triển ban đầu

**Giai đoạn sau:** PostgreSQL
- nếu cần concurrency tốt hơn
- nếu cần nhiều worker/process
- nếu cần retention/log lớn hơn

### 2.3 Quy ước naming

- tên bảng: `snake_case`, số nhiều
- khóa ngoại: `<entity>_id`
- timestamp: ISO UTC ở tầng ứng dụng; ở DB lưu `TEXT` hoặc `TIMESTAMP`
- soft-delete chỉ dùng khi thực sự cần; MVP ưu tiên `status`

---

## 3. Mô hình quan hệ tổng quan

```text
sessions
  ├── session_participants
  ├── messages
  │     ├── message_mentions
  │     └── message_artifacts (logical via artifacts.source_message_id)
  ├── jobs
  │     ├── job_events
  │     ├── artifacts
  │     ├── approval_requests
  │     └── relay_edges
  └── session_events

agents
  ├── agent_runtimes
  ├── session_participants
  ├── jobs
  ├── messages
  ├── approval_requests
  └── presence_heartbeats
```

### 3.1 Quan hệ cốt lõi

- Một `session` có nhiều `session_participants`
- Một `session` có nhiều `messages`
- Một `message` có thể mention nhiều `agents`
- Một `message` có thể tạo ra một hoặc nhiều `jobs`
- Một `job` được gán cho đúng một `agent`
- Một `job` có thể sinh nhiều `artifacts`
- Một `job` có thể có nhiều `approval_requests`
- Một `agent` có thể tham gia nhiều `sessions`
- Một `agent` có thể có một hoặc nhiều `agent_runtimes`
- Một `runtime` có thể map tới nhiều `codex_thread_id` theo từng session/job

---

## 4. Danh sách bảng cho MVP

## 4.1 `sessions`

Lưu thông tin session cộng tác.

### Mục đích

- tạo không gian chat chung
- lưu metadata chính của collaboration
- xác định lead và trạng thái session

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `ses_001` hoặc UUID |
| `title` | TEXT | Có | tên session |
| `goal` | TEXT | Không | mục tiêu tổng quát |
| `status` | TEXT | Có | `draft`, `active`, `paused`, `completed`, `archived` |
| `lead_agent_id` | TEXT | Không | FK tới `agents.id` |
| `active_phase_id` | TEXT | Không | để dành cho phase engine sau này |
| `loop_guard_status` | TEXT | Có | `normal`, `warning`, `paused` |
| `loop_guard_reason` | TEXT | Không | lý do nếu bị pause |
| `last_message_at` | TEXT | Không | phục vụ sort danh sách session |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Ràng buộc

- `status` thuộc tập cho phép
- `lead_agent_id` có thể null khi session còn draft

### Index đề xuất

- `idx_sessions_status`
- `idx_sessions_last_message_at`
- `idx_sessions_lead_agent_id`

---

## 4.2 `agents`

Lưu danh tính logic của agent.

### Mục đích

- quản lý tên hiển thị
- quản lý vai trò
- đánh dấu lead/non-lead mặc định
- lưu capability cơ bản

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `agt_builder` |
| `display_name` | TEXT | Có | tên hiển thị, nên unique |
| `role` | TEXT | Có | `planner`, `builder`, `reviewer`, ... |
| `is_lead_default` | INTEGER | Có | 0/1 |
| `runtime_kind` | TEXT | Có | `codex` cho MVP |
| `capabilities_json` | TEXT | Không | JSON string |
| `default_config_json` | TEXT | Không | model, sandbox, policy mặc định |
| `status` | TEXT | Có | `active`, `disabled`, `archived` |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `ux_agents_display_name`
- `idx_agents_role`
- `idx_agents_status`

---

## 4.3 `agent_runtimes`

Lưu runtime thực thi thực tế của agent.

### Mục đích

- tách `agent` logic khỏi process/runtime thật
- cho phép một agent có runtime riêng
- lưu trạng thái runtime và thông tin kết nối

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `rt_codex_builder` |
| `agent_id` | TEXT | Có | FK tới `agents.id` |
| `runtime_kind` | TEXT | Có | `codex_app_server` |
| `transport_kind` | TEXT | Có | `stdio`, `ws`, `local_socket` |
| `transport_config_json` | TEXT | Không | command, args, env, socket path |
| `workspace_path` | TEXT | Không | cwd mặc định |
| `approval_policy` | TEXT | Không | runtime default |
| `sandbox_policy` | TEXT | Không | runtime default |
| `runtime_status` | TEXT | Có | `starting`, `online`, `offline`, `crashed`, `busy` |
| `last_heartbeat_at` | TEXT | Không | UTC |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_agent_runtimes_agent_id`
- `idx_agent_runtimes_runtime_status`

---

## 4.4 `session_participants`

Lưu membership của agent trong session.

### Mục đích

- xác định agent nào tham gia session nào
- lưu permission/read scope/write scope
- ghi lại thời điểm join/leave

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | có thể là UUID |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `agent_id` | TEXT | Có | FK tới `agents.id` |
| `runtime_id` | TEXT | Không | FK tới `agent_runtimes.id` |
| `is_lead` | INTEGER | Có | 0/1 trong ngữ cảnh session |
| `read_scope` | TEXT | Có | `shared_history`, `summary_only`, `custom` |
| `write_scope` | TEXT | Có | `mention_or_direct_assignment`, `full`, `read_only` |
| `participant_status` | TEXT | Có | `invited`, `joined`, `left`, `removed` |
| `joined_at` | TEXT | Không | UTC |
| `left_at` | TEXT | Không | UTC |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Ràng buộc

- unique `(session_id, agent_id)`

### Index đề xuất

- `ux_session_participants_session_agent`
- `idx_session_participants_session_id`
- `idx_session_participants_agent_id`

---

## 4.5 `messages`

Lưu tất cả chat/message/system event nhìn thấy trong session.

### Mục đích

- lưu transcript chung
- phân biệt chat, command, relay, status
- gắn message vào sender và session

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `msg_001` |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `sender_type` | TEXT | Có | `user`, `agent`, `system` |
| `sender_id` | TEXT | Không | user local id hoặc `agents.id` |
| `message_type` | TEXT | Có | `chat`, `command`, `relay`, `status`, `approval_request`, `approval_decision`, `artifact_notice` |
| `content` | TEXT | Có | text hiển thị |
| `content_format` | TEXT | Có | `plain_text`, `markdown`, `json` |
| `reply_to_message_id` | TEXT | Không | FK self-reference |
| `source_message_id` | TEXT | Không | message gốc nếu đây là relay/system derivative |
| `visibility` | TEXT | Có | `session`, `system_only`, `lead_only` |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_messages_session_id_created_at`
- `idx_messages_sender_id`
- `idx_messages_reply_to_message_id`
- `idx_messages_source_message_id`

---

## 4.6 `message_mentions`

Tách mention ra bảng riêng để query nhanh.

### Mục đích

- biết message nào mention agent nào
- hỗ trợ routing và audit

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | UUID |
| `message_id` | TEXT | Có | FK tới `messages.id` |
| `mentioned_agent_id` | TEXT | Có | FK tới `agents.id` |
| `mention_text` | TEXT | Có | ví dụ `#builder` |
| `mention_order` | INTEGER | Có | thứ tự trong message |
| `created_at` | TEXT | Có | UTC |

### Ràng buộc

- unique `(message_id, mentioned_agent_id, mention_order)`

### Index đề xuất

- `idx_message_mentions_message_id`
- `idx_message_mentions_mentioned_agent_id`

---

## 4.7 `jobs`

Đơn vị công việc có trạng thái rõ ràng.

### Mục đích

- theo dõi assignment cho từng agent
- lưu mapping sang Codex thread/turn
- là trung tâm của artifact, approval, event

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `job_001` |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `assigned_agent_id` | TEXT | Có | FK tới `agents.id` |
| `runtime_id` | TEXT | Không | FK tới `agent_runtimes.id` |
| `source_message_id` | TEXT | Không | FK tới `messages.id` |
| `parent_job_id` | TEXT | Không | nếu job này do relay từ job khác |
| `title` | TEXT | Có | tóm tắt ngắn |
| `instructions` | TEXT | Không | prompt/assignment đã chuẩn hóa |
| `status` | TEXT | Có | `queued`, `running`, `input_required`, `auth_required`, `completed`, `failed`, `canceled`, `paused_by_loop_guard` |
| `hop_count` | INTEGER | Có | số hop relay hiện tại |
| `priority` | TEXT | Có | `low`, `normal`, `high` |
| `codex_runtime_id` | TEXT | Không | mirror field để debug nhanh |
| `codex_thread_id` | TEXT | Không | thread của Codex |
| `active_turn_id` | TEXT | Không | turn đang chạy |
| `last_known_turn_status` | TEXT | Không | `running`, `completed`, `interrupted`, ... |
| `result_summary` | TEXT | Không | summary ngắn |
| `error_code` | TEXT | Không | nếu fail |
| `error_message` | TEXT | Không | nếu fail |
| `started_at` | TEXT | Không | UTC |
| `completed_at` | TEXT | Không | UTC |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_jobs_session_id`
- `idx_jobs_assigned_agent_id`
- `idx_jobs_status`
- `idx_jobs_source_message_id`
- `idx_jobs_parent_job_id`
- `idx_jobs_codex_thread_id`

---

## 4.8 `job_events`

Audit trail cho job lifecycle.

### Mục đích

- debug luồng chạy
- dựng timeline job
- recovery sau restart

### Các event ví dụ

- `job_created`
- `job_dispatched`
- `turn_started`
- `turn_output_delta`
- `turn_completed`
- `approval_required`
- `approval_accepted`
- `approval_declined`
- `input_required`
- `job_paused_by_loop_guard`
- `job_canceled`
- `job_failed`

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | UUID |
| `job_id` | TEXT | Có | FK tới `jobs.id` |
| `session_id` | TEXT | Có | denormalized để query nhanh |
| `event_type` | TEXT | Có | tên event |
| `event_payload_json` | TEXT | Không | JSON string |
| `created_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_job_events_job_id_created_at`
- `idx_job_events_session_id_created_at`
- `idx_job_events_event_type`

---

## 4.9 `artifacts`

Lưu output hữu ích do job sinh ra.

### Mục đích

- hiển thị kết quả có cấu trúc
- gắn artifact vào job/session/message
- chuẩn bị cho A2A artifact mapping sau này

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `art_001` |
| `job_id` | TEXT | Có | FK tới `jobs.id` |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `source_message_id` | TEXT | Không | message làm phát sinh artifact notice |
| `artifact_type` | TEXT | Có | `final_text`, `diff`, `file`, `json`, `log_excerpt` |
| `title` | TEXT | Có | tiêu đề ngắn |
| `content_text` | TEXT | Không | cho text/diff/log |
| `file_path` | TEXT | Không | đường dẫn local export |
| `file_name` | TEXT | Không | tên file |
| `mime_type` | TEXT | Không | ví dụ `text/plain` |
| `size_bytes` | INTEGER | Không | kích thước file |
| `checksum_sha256` | TEXT | Không | nếu có |
| `metadata_json` | TEXT | Không | JSON string |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_artifacts_job_id`
- `idx_artifacts_session_id`
- `idx_artifacts_artifact_type`

---

## 4.10 `approval_requests`

Lưu các yêu cầu xin xác nhận trước khi tiếp tục job.

### Mục đích

- map approval của Codex sang state nội bộ
- cho phép lead/user ra quyết định
- hỗ trợ resume sau restart

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | ví dụ `apr_001` |
| `job_id` | TEXT | Có | FK tới `jobs.id` |
| `agent_id` | TEXT | Có | FK tới `agents.id` |
| `approval_type` | TEXT | Có | `command_execution`, `file_change`, `network_access`, `custom` |
| `status` | TEXT | Có | `pending`, `accepted`, `declined`, `canceled` |
| `request_payload_json` | TEXT | Có | command/file/network payload |
| `decision_payload_json` | TEXT | Không | ai duyệt, ghi chú gì |
| `requested_at` | TEXT | Có | UTC |
| `resolved_at` | TEXT | Không | UTC |
| `created_at` | TEXT | Có | UTC |
| `updated_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_approval_requests_job_id`
- `idx_approval_requests_agent_id`
- `idx_approval_requests_status`

---

## 4.11 `presence_heartbeats`

Lưu heartbeat/presence theo runtime hoặc agent.

### Mục đích

- xác định agent online/offline
- hỗ trợ queue khi agent tạm offline
- hỗ trợ dashboard/diagnostics

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | UUID |
| `agent_id` | TEXT | Có | FK tới `agents.id` |
| `runtime_id` | TEXT | Không | FK tới `agent_runtimes.id` |
| `presence` | TEXT | Có | `online`, `offline`, `busy`, `unknown` |
| `heartbeat_at` | TEXT | Có | UTC |
| `details_json` | TEXT | Không | latency, pid, version |
| `created_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_presence_heartbeats_agent_id_heartbeat_at`
- `idx_presence_heartbeats_runtime_id_heartbeat_at`

> Ghi chú: bảng này là log history. Trạng thái hiện tại nên đọc nhanh từ `agent_runtimes.runtime_status` hoặc cache/service layer.

---

## 4.12 `relay_edges`

Lưu quan hệ relay giữa nguồn và đích để kiểm soát loop.

### Mục đích

- theo dõi output từ job/message nào được relay sang agent nào
- kiểm soát hop count và chuỗi gọi qua lại
- giải thích vì sao một agent bị kích hoạt

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | UUID |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `source_message_id` | TEXT | Không | message nguồn |
| `source_job_id` | TEXT | Không | job nguồn |
| `target_agent_id` | TEXT | Có | agent được giao tiếp |
| `target_job_id` | TEXT | Không | job đích nếu đã tạo |
| `relay_reason` | TEXT | Có | `mention`, `policy_auto_relay`, `manual_relay` |
| `hop_number` | INTEGER | Có | hop hiện tại |
| `created_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_relay_edges_session_id_created_at`
- `idx_relay_edges_source_job_id`
- `idx_relay_edges_target_agent_id`

---

## 4.13 `session_events`

Lưu event cấp session.

### Mục đích

- audit tạo session, join/leave, pause, compact, loop guard
- dựng activity feed cấp session

### Event ví dụ

- `session_created`
- `participant_joined`
- `participant_left`
- `session_paused`
- `session_resumed`
- `loop_guard_triggered`
- `compact_requested`
- `compact_completed`

### Cột đề xuất

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---:|---|
| `id` | TEXT | Có | UUID |
| `session_id` | TEXT | Có | FK tới `sessions.id` |
| `event_type` | TEXT | Có | tên event |
| `actor_type` | TEXT | Không | `user`, `agent`, `system` |
| `actor_id` | TEXT | Không | id tác nhân |
| `event_payload_json` | TEXT | Không | JSON string |
| `created_at` | TEXT | Có | UTC |

### Index đề xuất

- `idx_session_events_session_id_created_at`
- `idx_session_events_event_type`

---

## 5. Bảng nên để sang giai đoạn sau

Các bảng dưới đây hữu ích nhưng **chưa bắt buộc cho MVP**.

### 5.1 `phases`

Dùng khi bạn muốn structured sessions nhiều pha như planning / build / review.

### 5.2 `rules`

Dùng khi muốn lưu rule/policy được đề xuất và được activate bởi con người.

### 5.3 `job_inputs`

Dùng khi muốn track nhiều input source cho một job theo kiểu normalized.

### 5.4 `attachments`

Dùng khi muốn upload file thật thay vì chỉ artifact export.

### 5.5 `a2a_tasks`

Dùng khi expose public A2A layer và muốn map rõ giữa `job/session` nội bộ với `task/contextId` của A2A.

---

## 6. Khóa ngoại và quy tắc xóa dữ liệu

### 6.1 Khuyến nghị cho MVP

- Không dùng cascade delete bừa bãi
- Session thường nên **archive**, không delete cứng
- Message/job/artifact/event nên giữ để debug

### 6.2 Gợi ý hành vi

- `sessions` → `session_participants`: không xóa cứng, archive session
- `sessions` → `messages/jobs/artifacts`: giữ lại
- `agents` → `session_participants/jobs/messages`: không xóa cứng; đổi `status = archived`
- `jobs` → `job_events/artifacts/approval_requests`: có thể cascade nếu delete test data trong môi trường dev, nhưng production nên giữ

---

## 7. Chỉ mục tối thiểu nên có ngay

Đây là bộ index quan trọng nhất cho MVP:

1. `messages(session_id, created_at)`
2. `jobs(session_id, status)`
3. `jobs(assigned_agent_id, status)`
4. `artifacts(job_id)`
5. `approval_requests(job_id, status)`
6. `session_participants(session_id, agent_id)` unique
7. `message_mentions(mentioned_agent_id, created_at)` nếu DB hỗ trợ thêm cột timestamp/index phù hợp
8. `relay_edges(session_id, created_at)`
9. `session_events(session_id, created_at)`
10. `job_events(job_id, created_at)`

---

## 8. SQL DDL gợi ý cho SQLite (MVP)

> Đây là bản DDL định hướng. Khi implement, bạn có thể tách thành nhiều migration nhỏ.

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  goal TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'completed', 'archived')),
  lead_agent_id TEXT,
  active_phase_id TEXT,
  loop_guard_status TEXT NOT NULL DEFAULT 'normal' CHECK (loop_guard_status IN ('normal', 'warning', 'paused')),
  loop_guard_reason TEXT,
  last_message_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (lead_agent_id) REFERENCES agents(id)
);

CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL,
  is_lead_default INTEGER NOT NULL DEFAULT 0,
  runtime_kind TEXT NOT NULL,
  capabilities_json TEXT,
  default_config_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled', 'archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE agent_runtimes (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  runtime_kind TEXT NOT NULL,
  transport_kind TEXT NOT NULL,
  transport_config_json TEXT,
  workspace_path TEXT,
  approval_policy TEXT,
  sandbox_policy TEXT,
  runtime_status TEXT NOT NULL CHECK (runtime_status IN ('starting', 'online', 'offline', 'crashed', 'busy')),
  last_heartbeat_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE session_participants (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  runtime_id TEXT,
  is_lead INTEGER NOT NULL DEFAULT 0,
  read_scope TEXT NOT NULL,
  write_scope TEXT NOT NULL,
  participant_status TEXT NOT NULL CHECK (participant_status IN ('invited', 'joined', 'left', 'removed')),
  joined_at TEXT,
  left_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (session_id, agent_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id)
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'agent', 'system')),
  sender_id TEXT,
  message_type TEXT NOT NULL CHECK (message_type IN ('chat', 'command', 'relay', 'status', 'approval_request', 'approval_decision', 'artifact_notice')),
  content TEXT NOT NULL,
  content_format TEXT NOT NULL DEFAULT 'plain_text' CHECK (content_format IN ('plain_text', 'markdown', 'json')),
  reply_to_message_id TEXT,
  source_message_id TEXT,
  visibility TEXT NOT NULL DEFAULT 'session' CHECK (visibility IN ('session', 'system_only', 'lead_only')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (reply_to_message_id) REFERENCES messages(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE message_mentions (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  mentioned_agent_id TEXT NOT NULL,
  mention_text TEXT NOT NULL,
  mention_order INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (message_id, mentioned_agent_id, mention_order),
  FOREIGN KEY (message_id) REFERENCES messages(id),
  FOREIGN KEY (mentioned_agent_id) REFERENCES agents(id)
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  assigned_agent_id TEXT NOT NULL,
  runtime_id TEXT,
  source_message_id TEXT,
  parent_job_id TEXT,
  title TEXT NOT NULL,
  instructions TEXT,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'input_required', 'auth_required', 'completed', 'failed', 'canceled', 'paused_by_loop_guard')),
  hop_count INTEGER NOT NULL DEFAULT 0,
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
  codex_runtime_id TEXT,
  codex_thread_id TEXT,
  active_turn_id TEXT,
  last_known_turn_status TEXT,
  result_summary TEXT,
  error_code TEXT,
  error_message TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (assigned_agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id),
  FOREIGN KEY (parent_job_id) REFERENCES jobs(id)
);

CREATE TABLE job_events (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  source_message_id TEXT,
  artifact_type TEXT NOT NULL CHECK (artifact_type IN ('final_text', 'diff', 'file', 'json', 'log_excerpt')),
  title TEXT NOT NULL,
  content_text TEXT,
  file_path TEXT,
  file_name TEXT,
  mime_type TEXT,
  size_bytes INTEGER,
  checksum_sha256 TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE approval_requests (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  approval_type TEXT NOT NULL CHECK (approval_type IN ('command_execution', 'file_change', 'network_access', 'custom')),
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'declined', 'canceled')),
  request_payload_json TEXT NOT NULL,
  decision_payload_json TEXT,
  requested_at TEXT NOT NULL,
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE presence_heartbeats (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  runtime_id TEXT,
  presence TEXT NOT NULL CHECK (presence IN ('online', 'offline', 'busy', 'unknown')),
  heartbeat_at TEXT NOT NULL,
  details_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id)
);

CREATE TABLE relay_edges (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  source_message_id TEXT,
  source_job_id TEXT,
  target_agent_id TEXT NOT NULL,
  target_job_id TEXT,
  relay_reason TEXT NOT NULL CHECK (relay_reason IN ('mention', 'policy_auto_relay', 'manual_relay')),
  hop_number INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id),
  FOREIGN KEY (source_job_id) REFERENCES jobs(id),
  FOREIGN KEY (target_agent_id) REFERENCES agents(id),
  FOREIGN KEY (target_job_id) REFERENCES jobs(id)
);

CREATE TABLE session_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_type TEXT,
  actor_id TEXT,
  event_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## 9. Trình tự migration khuyến nghị

Để người mới dễ làm, nên tách migration theo nhóm nhỏ:

### Migration 001
- `sessions`
- `agents`
- `agent_runtimes`
- `session_participants`

### Migration 002
- `messages`
- `message_mentions`

### Migration 003
- `jobs`
- `job_events`

### Migration 004
- `artifacts`
- `approval_requests`

### Migration 005
- `presence_heartbeats`
- `relay_edges`
- `session_events`

### Migration 006
- thêm indexes
- thêm backfill script nếu cần

---

## 10. Mapping schema sang API object

### 10.1 Session API
- `sessions` → object `session`
- `session_participants` → participants list

### 10.2 Agent API
- `agents` + `agent_runtimes` → object `agent`

### 10.3 Message API
- `messages` + `message_mentions` → object `message`

### 10.4 Job API
- `jobs` + `job_events` → object `job`

### 10.5 Artifact API
- `artifacts` → object `artifact`

### 10.6 Approval API
- `approval_requests` → object `approval_request`

---

## 11. Mapping schema sang Codex app-server

Schema này không mirror toàn bộ event của Codex 1:1. Thay vào đó, nó giữ các trường cần thiết để coordinator hoạt động ổn định:

- `jobs.codex_thread_id` ↔ thread của Codex
- `jobs.active_turn_id` ↔ turn đang chạy
- `jobs.last_known_turn_status` ↔ trạng thái turn gần nhất
- `approval_requests` ↔ approval event từ Codex
- `artifacts` ↔ final text / diff / file export sinh từ output của Codex
- `job_events.event_payload_json` ↔ raw hoặc normalized event từ bridge

Điều này giúp:
- không khóa schema quá chặt vào version nội bộ của Codex
- vẫn đủ dữ liệu để resume/debug
- dễ đổi bridge hoặc đổi runtime sau này

---

## 12. Khuyến nghị chốt cho MVP

Nếu phải bắt đầu ngay, hãy implement theo thứ tự này:

1. `sessions`
2. `agents`
3. `agent_runtimes`
4. `session_participants`
5. `messages`
6. `message_mentions`
7. `jobs`
8. `job_events`
9. `artifacts`
10. `approval_requests`
11. `presence_heartbeats`
12. `relay_edges`
13. `session_events`

Với thứ tự này, bạn sẽ có:
- transcript chung trước
- routing cơ bản trước
- job lifecycle sau
- artifact/approval sau nữa
- presence và relay audit ở cuối

---

## 13. Quyết định cuối cùng cho bản đầu

### Bắt buộc cho MVP
- `sessions`
- `agents`
- `agent_runtimes`
- `session_participants`
- `messages`
- `message_mentions`
- `jobs`
- `job_events`
- `artifacts`
- `approval_requests`
- `relay_edges`

### Nên có cho MVP nếu còn thời gian
- `presence_heartbeats`
- `session_events`

### Để sau
- `phases`
- `rules`
- `attachments`
- `a2a_tasks`

