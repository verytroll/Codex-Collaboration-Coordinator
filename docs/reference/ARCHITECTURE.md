# ARCHITECTURE.md

# Kiến trúc hệ thống: Codex Collaboration Coordinator

## 1. Mục tiêu kiến trúc

Tài liệu này mô tả kiến trúc đề xuất cho hệ thống điều phối nhiều Codex agent có thể:

- cùng tham gia một session chung
- nhắn/giao việc cho nhau bằng mention như `#agent`
- chia sẻ lịch sử hội thoại chung
- được điều phối bởi một coordinator trung tâm
- chạy trên nền `codex app-server`
- có thể mở rộng ra A2A ở giai đoạn sau

Kiến trúc được chọn theo nguyên tắc:

- **Không fork Codex ở giai đoạn đầu**
- **Dùng coordinator riêng** để điều phối agent
- **Dùng Codex app-server như execution engine**
- **Tách UX cộng tác khỏi runtime thực thi**
- **Thiết kế từng lớp độc lập để dễ thay thế và mở rộng**

---

## 2. Nguyên tắc thiết kế

### 2.1 Tách vai trò rõ ràng

Hệ thống chia thành 3 lớp chính:

1. **Presentation / Interface layer**
   - CLI, web UI, hoặc API client
   - nơi người dùng nhìn thấy session, message, agent, control commands

2. **Coordination layer**
   - session manager
   - router
   - relay engine
   - policy / loop guard
   - state store

3. **Execution layer**
   - từng Codex runtime
   - `codex app-server`
   - workspace / repo / sandbox thực thi

### 2.2 Một session, nhiều agent

Session là không gian cộng tác chung.

Mỗi agent trong session có:

- tên riêng
- vai trò riêng
- thread Codex riêng
- output riêng
- khả năng đọc lịch sử chung ở mức read-only hoặc có chọn lọc

### 2.3 Agent không nói chuyện trực tiếp với nhau

Agent A không gọi agent B trực tiếp.

Thay vào đó:

- Agent A gửi output cho coordinator
- Coordinator quyết định có relay sang B hay không
- Coordinator tạo message mới cho B
- B trả lời coordinator
- Coordinator phát lại vào session chung

Thiết kế này giúp:

- kiểm soát vòng lặp
- lưu đầy đủ transcript
- áp policy dễ hơn
- debug dễ hơn

### 2.4 Event-driven trước, realtime sau

Mọi thay đổi đều được ghi thành event nội bộ trước:

- message created
- task assigned
- agent started turn
- agent produced output
- approval required
- agent interrupted
- phase advanced

Sau đó mới phát ra cho UI hoặc API client.

---

## 3. Kiến trúc tổng thể

```text
User / Lead Agent / API Client
            |
            v
+----------------------------------+
| Interface Layer                  |
|----------------------------------|
| CLI / Web UI / HTTP API          |
+----------------------------------+
            |
            v
+----------------------------------+
| Coordinator Layer                |
|----------------------------------|
| Session Manager                  |
| Agent Registry                   |
| Router                           |
| Relay Engine                     |
| Command Handler                  |
| Loop Guard                       |
| Approval Manager                 |
| Presence Tracker                 |
| Artifact Manager                 |
| Event Bus                        |
| State Store                      |
+----------------------------------+
            |
            v
+----------------------------------+
| Codex Bridge Layer               |
|----------------------------------|
| Process Manager                  |
| JSON-RPC Client                  |
| Thread/Turn Mapper               |
| Event Translator                 |
+----------------------------------+
            |
            v
+----------------------------------+
| Execution Layer                  |
|----------------------------------|
| Codex Runtime A                  |
| Codex Runtime B                  |
| ...                              |
| Workspace / Repo / Sandbox       |
+----------------------------------+
```

---

## 4. Các thành phần cốt lõi

## 4.1 Interface Layer

### Nhiệm vụ

- nhận input từ người dùng
- hiển thị session và transcript
- gửi control commands
- hiển thị trạng thái agent và artifacts

### Thành phần có thể có

- CLI nội bộ
- Web UI
- HTTP API
- A2A adapter trong giai đoạn sau

### Trách nhiệm

- không chứa logic điều phối lõi
- chỉ gọi coordinator thông qua API/service layer

---

## 4.2 Session Manager

### Nhiệm vụ

Quản lý vòng đời session:

- tạo session
- đóng session
- load session cũ
- thêm/xóa participants
- xác định lead
- lưu phase hiện tại
- lưu session config

### Dữ liệu chính

- `session_id`
- `title`
- `goal`
- `status`
- `lead_agent_id`
- `active_phase_id`
- `created_at`
- `updated_at`

---

## 4.3 Agent Registry

### Nhiệm vụ

Lưu danh tính và cấu hình từng agent:

- agent name
- role
- runtime binding
- Codex thread mapping
- trạng thái online/offline/busy
- capabilities

### Ví dụ

- `planner`
- `builder`
- `reviewer`
- `researcher`

---

## 4.4 Router

### Nhiệm vụ

Phân tích message và quyết định định tuyến.

Ví dụ:

- `#builder hãy tạo endpoint login`
- `#reviewer kiểm tra diff mới nhất`
- `#planner đề xuất bước tiếp theo`

### Chức năng

- parse mention
- xác định target agent
- validate permission
- chuyển tiếp thành assignment nội bộ

---

## 4.5 Relay Engine

### Nhiệm vụ

Biến output từ một agent thành input có cấu trúc cho agent khác.

### Ví dụ

1. Lead gửi `#planner phân tích bug`
2. Planner trả summary
3. Coordinator relay summary cho `#builder`
4. Builder viết code
5. Coordinator relay diff cho `#reviewer`
6. Reviewer đánh giá patch

### Luật relay

- relay thủ công theo mention
- relay tự động theo policy
- relay theo phase
- relay theo output type

---

## 4.6 Command Handler

### Nhiệm vụ

Xử lý control commands, ví dụ:

- `/new`
- `/interrupt`
- `/compact`
- `/agents`
- `/status`
- `/phase`

### Quy tắc

- chỉ lead hoặc user có quyền mới được thực hiện một số command
- command có thể áp dụng lên session hoặc một agent cụ thể

---

## 4.7 Loop Guard

### Nhiệm vụ

Ngăn agent gọi qua lại vô hạn.

### Quy tắc gợi ý

- tối đa `N` lần relay liên tiếp không có user intervention
- tối đa `M` message tự động trong một session window
- phát cảnh báo khi A -> B -> A -> B lặp quá ngưỡng
- chuyển session sang `paused_for_review`

### Lý do cần có

- tiết kiệm token
- tránh spam
- giúp session dễ kiểm soát

---

## 4.8 Approval Manager

### Nhiệm vụ

Xử lý các trường hợp Codex yêu cầu xác nhận:

- chạy command
- sửa file
- truy cập thứ nhạy cảm

### Trách nhiệm

- nhận approval request từ Codex bridge
- chuyển task/agent state thành `auth_required`
- đợi user hoặc lead approve/decline
- gửi quyết định ngược về runtime

---

## 4.9 Presence Tracker

### Nhiệm vụ

Theo dõi trạng thái agent:

- online
- offline
- busy
- idle
- waiting_for_input
- waiting_for_approval

### Nguồn dữ liệu

- heartbeat từ runtime wrapper
- process liveness
- turn state

---

## 4.10 Artifact Manager

### Nhiệm vụ

Quản lý kết quả sinh ra bởi agent:

- text artifact
- diff artifact
- file artifact
- revisit summary
- transcript excerpt

### Chức năng

- lưu metadata
- gắn artifact với message hoặc task
- export file nếu cần
- hiển thị artifact mới nhất trong session

---

## 4.11 Event Bus

### Nhiệm vụ

Là trục sống của hệ thống.

Mỗi thay đổi quan trọng sẽ phát event:

- `session.created`
- `message.created`
- `agent.assigned`
- `turn.started`
- `turn.completed`
- `approval.requested`
- `artifact.created`
- `phase.changed`

### Lợi ích

- dễ log
- dễ test
- dễ thêm realtime stream/WebSocket/SSE sau này
- dễ thêm analytics và audit log

---

## 4.12 State Store

### Nhiệm vụ

Lưu trạng thái bền.

### Đề xuất v1

- SQLite

### Có thể nâng cấp

- PostgreSQL khi cần scale lớn hơn

---

## 4.13 Codex Bridge

### Nhiệm vụ

Kết nối coordinator với `codex app-server`.

### Chức năng chính

- spawn/quản lý process `codex app-server`
- gửi request JSON-RPC
- nhận event stream
- map `session/agent/task` sang `thread/turn`
- translate event của Codex thành event nội bộ

### Primitive cần dùng

- `thread/start`
- `thread/resume`
- `turn/start`
- `turn/steer`
- `turn/interrupt`
- `thread/compact/start`

---

## 5. Mô hình runtime

Có 2 lựa chọn chính.

## 5.1 Phương án A: 1 app-server, nhiều thread

### Mô hình

- một process `codex app-server`
- mỗi agent có một thread riêng

### Ưu điểm

- đơn giản nhất
- ít process
- dễ debug
- hợp cho MVP

### Nhược điểm

- ít cô lập hơn
- dùng chung runtime nhiều hơn

## 5.2 Phương án B: nhiều app-server, mỗi agent một runtime

### Mô hình

- mỗi agent có process `codex app-server` riêng
- có thể có cwd/sandbox/policy riêng

### Ưu điểm

- cô lập tốt hơn
- hợp với agent specialization mạnh
- dễ chia repo/worktree riêng

### Nhược điểm

- phức tạp hơn
- tốn tài nguyên hơn

## Khuyến nghị cho v1

Dùng **Phương án A: 1 app-server, nhiều thread**.

---

## 6. Cấu trúc thư mục đề xuất

```text
project/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ sessions.py
│  │  ├─ messages.py
│  │  ├─ agents.py
│  │  ├─ commands.py
│  │  └─ tasks.py
│  ├─ coordinator/
│  │  ├─ session_manager.py
│  │  ├─ agent_registry.py
│  │  ├─ router.py
│  │  ├─ relay_engine.py
│  │  ├─ command_handler.py
│  │  ├─ loop_guard.py
│  │  ├─ approval_manager.py
│  │  ├─ presence_tracker.py
│  │  └─ artifact_manager.py
│  ├─ codex_bridge/
│  │  ├─ process_manager.py
│  │  ├─ jsonrpc_client.py
│  │  ├─ thread_mapper.py
│  │  ├─ event_translator.py
│  │  └─ runtime_pool.py
│  ├─ domain/
│  │  ├─ models.py
│  │  ├─ enums.py
│  │  ├─ events.py
│  │  └─ policies.py
│  ├─ db/
│  │  ├─ migrations/
│  │  ├─ repositories/
│  │  └─ sqlite.py
│  ├─ services/
│  │  ├─ session_service.py
│  │  ├─ messaging_service.py
│  │  ├─ task_service.py
│  │  └─ agent_service.py
│  └─ utils/
│     ├─ logging.py
│     ├─ time.py
│     └─ ids.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ docs/
|  |-- planning/
|  |-- reference/
|  |-- operations/
|  |-- integrations/
|  |-- operator/
|  |-- releases/
|  `-- features/
|-- scripts/
│  ├─ dev_start.sh
│  ├─ reset_db.sh
│  └─ run_demo.sh
└─ artifacts/
```

---

## 7. Mô hình dữ liệu đề xuất

## 7.1 Bảng `sessions`

```sql
sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  goal TEXT,
  status TEXT NOT NULL,
  lead_agent_id TEXT,
  active_phase_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

## 7.2 Bảng `agents`

```sql
agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  role TEXT,
  runtime_key TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

## 7.3 Bảng `session_agents`

```sql
session_agents (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  is_lead INTEGER NOT NULL DEFAULT 0,
  joined_at TEXT NOT NULL,
  UNIQUE(session_id, agent_id)
)
```

## 7.4 Bảng `messages`

```sql
messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  author_type TEXT NOT NULL,
  author_id TEXT,
  content TEXT NOT NULL,
  message_type TEXT NOT NULL,
  parent_message_id TEXT,
  created_at TEXT NOT NULL
)
```

## 7.5 Bảng `mentions`

```sql
mentions (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  target_agent_id TEXT NOT NULL,
  mention_type TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```

## 7.6 Bảng `codex_threads`

```sql
codex_threads (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  codex_thread_id TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(session_id, agent_id)
)
```

## 7.7 Bảng `tasks`

```sql
tasks (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  assigned_agent_id TEXT NOT NULL,
  source_message_id TEXT,
  status TEXT NOT NULL,
  title TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

## 7.8 Bảng `artifacts`

```sql
artifacts (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  task_id TEXT,
  agent_id TEXT,
  artifact_type TEXT NOT NULL,
  title TEXT,
  body TEXT,
  file_path TEXT,
  created_at TEXT NOT NULL
)
```

## 7.9 Bảng `pending_approvals`

```sql
pending_approvals (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  task_id TEXT,
  approval_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

## 7.10 Bảng `event_log`

```sql
event_log (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```

---

## 8. Luồng `#agent` từ đầu đến cuối

Ví dụ người dùng gửi:

```text
#builder hãy tạo API /healthz bằng FastAPI
```

### Bước 1: Nhận message

- Interface layer nhận message
- lưu vào bảng `messages`
- phát event `message.created`

### Bước 2: Parse mention

- Router phát hiện mention `#builder`
- tìm agent `builder` trong session
- validate builder đang active

### Bước 3: Tạo task nội bộ

- tạo bản ghi `tasks`
- gắn `assigned_agent_id = builder`
- trạng thái ban đầu: `queued`

### Bước 4: Lấy thread của builder

- nếu chưa có thread Codex cho agent này trong session:
  - tạo mới qua `thread/start`
- nếu đã có:
  - dùng `thread/resume` hoặc giữ mapping hiện tại

### Bước 5: Bắt đầu turn

- Codex bridge gọi `turn/start`
- payload là message đã chuẩn hóa cho builder
- trạng thái task chuyển thành `working`
- presence agent thành `busy`

### Bước 6: Nhận event từ Codex

- delta text
- agent message
- diff update
- file changes
- approval request
- user input request
- turn completed

### Bước 7: Translate event

Event translator đổi event Codex thành event nội bộ:

- `turn.started`
- `artifact.created`
- `approval.requested`
- `task.updated`
- `turn.completed`

### Bước 8: Ghi artifact

Ví dụ:

- text summary
- code diff
- file artifact

### Bước 9: Publish vào session

Coordinator tạo message hệ thống hoặc agent message mới trong session:

- từ builder
- có link đến artifact mới nhất
- nếu cần có revisit summary

### Bước 10: Nếu cần relay tiếp

Nếu lead hoặc policy yêu cầu:

- Router sẽ chuyển output sang `#reviewer`
- bắt đầu một task mới kế thừa từ task trước

---

## 9. Luồng `/interrupt`

### Mục tiêu

Dừng agent đang chạy.

### Các bước

1. User hoặc lead gửi `/interrupt builder`
2. Command handler xác nhận quyền
3. Tìm active task của `builder`
4. Codex bridge gọi `turn/interrupt`
5. task chuyển sang `interrupted`
6. session nhận system message thông báo

---

## 10. Luồng `/compact`

### Mục tiêu

Nén bớt context của thread để tiếp tục làm việc lâu dài.

### Các bước

1. User hoặc lead gửi `/compact builder`
2. Command handler xác định thread hiện tại của builder
3. Codex bridge gọi `thread/compact/start`
4. tạo compact summary artifact
5. gắn summary vào session history dưới dạng revisit summary

---

## 11. Luồng approval

### Mục tiêu

Xử lý trường hợp Codex cần sự cho phép.

### Các bước

1. Codex bridge nhận event approval
2. Approval manager tạo `pending_approval`
3. task state -> `auth_required`
4. UI/CLI hiển thị yêu cầu cho lead hoặc user
5. người dùng chọn approve/decline
6. quyết định được gửi ngược lại bridge/runtime
7. task tiếp tục hoặc dừng

---

## 12. Luồng input required

### Mục tiêu

Cho phép agent hỏi lại khi thiếu thông tin.

### Các bước

1. runtime phát user-input request
2. task state -> `input_required`
3. session hiển thị câu hỏi
4. user trả lời trong session hoặc command riêng
5. coordinator gửi câu trả lời vào turn mới hoặc steer turn hiện tại
6. task tiếp tục

---

## 13. Phases và structured collaboration

Phần này có thể để v2/v3, nhưng nên thiết kế chỗ đặt trước.

## 13.1 Khái niệm

Một session có thể chia thành nhiều phase:

- planning
- implementation
- review
- revise
- finalize

## 13.2 Lợi ích

- agent biết mình đang ở giai đoạn nào
- policy relay rõ hơn
- history dễ đọc hơn

## 13.3 Dữ liệu đề xuất

```sql
phases (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  phase_order INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

---

## 14. Tích hợp A2A trong tương lai

Khi lõi coordinator ổn định, có thể thêm `A2AAdapter` như một lớp ngoài.

### Vai trò

- public agent card
- expose task API
- expose streaming
- biến session/task nội bộ thành tài nguyên A2A

### Mapping đề xuất

- `session` nội bộ = collaboration room
- `task` nội bộ = một assignment cụ thể
- `codex thread` = execution context của một agent trong session
- `artifact` nội bộ = output cho A2A artifact

---

## 15. Quan sát, log và debug

## 15.1 Logging tối thiểu

Mỗi log nên có:

- timestamp
- request_id
- session_id
- agent_id
- task_id
- codex_thread_id
- event_type

## 15.2 Audit trail

Mọi hành động điều phối quan trọng nên ghi event log:

- ai mention ai
- ai interrupt ai
- task nào sinh artifact nào
- approval nào đã được chấp thuận

## 15.3 Debug view nên có ở v2

- active sessions
- active agents
- pending approvals
- queued tasks
- recent artifacts
- relay chain view

---

## 16. Quyết định kiến trúc chốt cho v1

### Chọn

- Python + FastAPI
- SQLite
- 1 `codex app-server`
- nhiều thread Codex
- coordinator riêng
- session-based collaboration
- `#agent` mention routing
- `/interrupt` và `/compact`
- artifact manager
- loop guard cơ bản

### Chưa chọn ở v1

- fork Codex
- multi-tenant auth production
- web UI lớn
- webhook push notifications
- multi-runtime pool phức tạp
- phase engine đầy đủ
- A2A public API hoàn chỉnh

---

## 17. MVP checklist kiến trúc

Một bản v1 được xem là đạt khi có đủ:

- tạo session
- thêm ít nhất 2 agent vào session
- gửi `#agent` thành công
- agent được gọi qua Codex thread riêng
- output được đưa lại vào session
- `/interrupt` hoạt động
- `/compact` hoạt động
- approval/input-required được xử lý
- artifact text/diff được lưu
- loop guard cơ bản hoạt động
- transcript được lưu bền qua restart

---

## 18. Mở rộng sau MVP

### V2

- web UI
- roles và jobs
- phase presets
- revisit summary nâng cao
- multi-channel hoặc sub-rooms

### V3

- A2A adapter public
- nhiều runtime pool
- repo/worktree riêng theo agent
- policy auto-approve có điều kiện
- review mode và orchestration nâng cao

---

## 19. Kết luận

Kiến trúc này kết hợp:

- **trải nghiệm cộng tác kiểu `codex-weave`**: session, mentions, lead, interrupt, compact
- **tư duy hệ thống kiểu `agentchattr`**: coordinator độc lập, router, loop guard, presence, jobs/phases về sau
- **execution engine của Codex app-server**: thread, turn, interrupt, compact, approval

Nó phù hợp với mục tiêu hiện tại vì:

- dễ làm bản đầu
- không khóa sớm vào fork Codex
- có thể phát triển thành hệ đa agent thật sự
- có đường mở rộng ra A2A về sau
