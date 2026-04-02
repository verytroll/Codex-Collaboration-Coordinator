# IMPLEMENTATION_TASKS.md

# Danh sách nhiệm vụ triển khai: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/archive/PLAN.md` thành backlog thực thi chi tiết hơn.

Khác với `docs/planning/archive/PLAN.md`:

- `docs/planning/archive/PLAN.md` nói về **lộ trình và mốc lớn**
- `docs/planning/archive/IMPLEMENTATION_TASKS.md` nói về **việc cần code cụ thể**, theo module, file và thứ tự phụ thuộc

Mỗi task trong tài liệu này được thiết kế để:

- đủ nhỏ để triển khai trong một bước
- đủ lớn để tạo ra kết quả thấy được
- có liên kết phụ thuộc rõ ràng
- đi từ nền tảng tới MVP mà không nhảy độ phức tạp quá lớn

---

## 2. Quy ước

### 2.1 Trạng thái task

- `Not started`
- `In progress`
- `Blocked`
- `Done`

### 2.2 Mẫu mô tả task

Mỗi task có các phần:

- **ID**
- **Mục tiêu**
- **Phụ thuộc**
- **File hoặc module chính**
- **Việc cần làm**
- **Kết quả đầu ra**
- **Điều kiện hoàn thành**

### 2.3 Quy tắc phụ thuộc

- Không có task nào đứng một mình
- Task đầu tiên của một nhóm phụ thuộc vào task cuối của nhóm trước hoặc task nền liên quan
- Nếu một task cần dữ liệu, API hoặc runtime từ task khác, phải ghi rõ phụ thuộc

---

## 3. Sơ đồ phụ thuộc tổng thể

**F01 → F02 → F03 → F04 → F05 → F06 → F07 → F08 → F09 → F10 → F11 → F12 → F13 → F14 → F15 → F16**

Trong đó:

- F01-F03: nền tảng app và hạ tầng code
- F04-F06: database và state store
- F07-F09: coordinator API cơ bản
- F10-F11: CodexBridge và job execution
- F12-F13: routing, relay, control commands
- F14: presence, recovery, loop guard
- F15: artifacts, approval, streaming
- F16: polish, docs, A2A-ready surface

---

## 4. Backlog chi tiết

## F01. Tạo skeleton dự án
**Phụ thuộc:** không  
**Mở khóa:** F02  
**File hoặc module chính:** `app/`, `tests/`, `scripts/`, `README.md`

### Việc cần làm
1. Tạo cấu trúc thư mục ban đầu:
   - `app/api/`
   - `app/core/`
   - `app/db/`
   - `app/repositories/`
   - `app/services/`
   - `app/codex_bridge/`
   - `app/models/`
   - `tests/unit/`
   - `tests/integration/`
2. Tạo file `app/main.py`
3. Tạo file cấu hình môi trường
4. Tạo README ngắn cho dev setup

### Kết quả đầu ra
- repo có skeleton ổn định

### Điều kiện hoàn thành
- cấu trúc thư mục đúng
- app import được mà chưa lỗi vòng lặp module

---

## F02. Cấu hình toolchain và chất lượng mã nguồn
**Phụ thuộc:** F01  
**Mở khóa:** F03  
**File hoặc module chính:** `pyproject.toml`, `.env.example`, `Makefile` hoặc script tương đương

### Việc cần làm
1. Cài và cấu hình dependencies nền
2. Cấu hình `pytest`
3. Cấu hình lint/format
4. Tạo script chạy app, test, lint
5. Tạo `GET /api/v1/healthz`

### Kết quả đầu ra
- app chạy local được
- test đầu tiên pass

### Điều kiện hoàn thành
- `healthz` trả 200
- lệnh test và lint chạy được

---

## F03. Tạo core app modules
**Phụ thuộc:** F02  
**Mở khóa:** F04  
**File hoặc module chính:** `app/core/config.py`, `app/core/logging.py`, `app/core/errors.py`

### Việc cần làm
1. Tạo config loader
2. Tạo logger chuẩn
3. Tạo error model chung cho API
4. Tạo request ID middleware cơ bản

### Kết quả đầu ra
- app có core config và logging dùng chung

### Điều kiện hoàn thành
- route lỗi trả theo format thống nhất
- log có request id hoặc trace cơ bản

---

## F04. Thiết lập migration framework
**Phụ thuộc:** F03  
**Mở khóa:** F05  
**File hoặc module chính:** `app/db/connection.py`, `app/db/migrations/`

### Việc cần làm
1. Tạo DB connection factory cho SQLite
2. Tạo cơ chế chạy migration
3. Tạo bảng quản lý migration version
4. Tạo test khởi tạo DB rỗng

### Kết quả đầu ra
- DB khởi tạo được từ lệnh migration

### Điều kiện hoàn thành
- chạy migration một lần tạo DB thành công
- chạy lần hai không phá DB

---

## F05. Tạo migration cho nhóm bảng nền
**Phụ thuộc:** F04  
**Mở khóa:** F06  
**File hoặc module chính:** `app/db/migrations/001_*.sql`, `002_*.sql`

### Việc cần làm
1. Tạo bảng `sessions`
2. Tạo bảng `agents`
3. Tạo bảng `agent_runtimes`
4. Tạo bảng `session_participants`
5. Tạo index tối thiểu cho các bảng trên

### Kết quả đầu ra
- DB có đủ bảng nền cho coordinator

### Điều kiện hoàn thành
- migration pass
- foreign key/ràng buộc chính hoạt động

---

## F06. Tạo migration cho nhóm bảng runtime và lịch sử
**Phụ thuộc:** F05  
**Mở khóa:** F07  
**File hoặc module chính:** `app/db/migrations/003_*.sql`, `004_*.sql`, `005_*.sql`

### Việc cần làm
1. Tạo bảng `messages`
2. Tạo bảng `message_mentions`
3. Tạo bảng `jobs`
4. Tạo bảng `job_events`
5. Tạo bảng `artifacts`
6. Tạo bảng `approval_requests`
7. Tạo bảng `presence_heartbeats`
8. Tạo bảng `relay_edges`
9. Tạo bảng `session_events`

### Kết quả đầu ra
- DB có đầy đủ schema MVP

### Điều kiện hoàn thành
- migration full pass từ DB rỗng
- test schema smoke pass

---

## F07. Tạo repository layer cho session và agent
**Phụ thuộc:** F06  
**Mở khóa:** F08  
**File hoặc module chính:** `app/repositories/sessions.py`, `agents.py`, `participants.py`

### Việc cần làm
1. Tạo session repository
2. Tạo agent repository
3. Tạo agent runtime repository
4. Tạo participant repository
5. Viết test CRUD cho các repository này

### Kết quả đầu ra
- session, agent, participant được lưu và đọc lại được

### Điều kiện hoàn thành
- test CRUD pass
- repository API rõ ràng, không lẫn logic HTTP

---

## F08. Tạo repository layer cho message và job
**Phụ thuộc:** F07  
**Mở khóa:** F09  
**File hoặc module chính:** `app/repositories/messages.py`, `jobs.py`, `artifacts.py`, `approvals.py`

### Việc cần làm
1. Tạo message repository
2. Tạo mention repository
3. Tạo job repository
4. Tạo job event repository
5. Tạo artifact repository
6. Tạo approval repository
7. Tạo presence repository
8. Tạo relay edge repository

### Kết quả đầu ra
- message/job/artifact có repository riêng

### Điều kiện hoàn thành
- test CRUD pass cho các bảng runtime

---

## F09. Tạo Session API và Agent API cơ bản
**Phụ thuộc:** F08  
**Mở khóa:** F10  
**File hoặc module chính:** `app/api/sessions.py`, `app/api/agents.py`, `app/models/api/*.py`

### Việc cần làm
1. Tạo Pydantic models cho Session và Agent
2. Implement:
   - `POST /api/v1/sessions`
   - `GET /api/v1/sessions`
   - `GET /api/v1/sessions/{session_id}`
   - `PATCH /api/v1/sessions/{session_id}`
   - `POST /api/v1/agents`
   - `GET /api/v1/agents`
   - `GET /api/v1/agents/{agent_id}`
   - `PATCH /api/v1/agents/{agent_id}`
3. Viết test API cho các route trên

### Kết quả đầu ra
- tạo session và agent qua HTTP được

### Điều kiện hoàn thành
- API contract khớp `docs/reference/API.md`
- test route pass

---

## F10. Tạo Participant API, Message API và event log cơ bản
**Phụ thuộc:** F09  
**Mở khóa:** F11  
**File hoặc module chính:** `app/api/participants.py`, `app/api/messages.py`, `app/services/session_events.py`

### Việc cần làm
1. Implement:
   - `POST /api/v1/sessions/{session_id}/participants`
   - `GET /api/v1/sessions/{session_id}/participants`
   - `DELETE /api/v1/sessions/{session_id}/participants/{agent_id}`
   - `POST /api/v1/sessions/{session_id}/messages`
   - `GET /api/v1/sessions/{session_id}/messages`
   - `GET /api/v1/messages/{message_id}`
2. Ghi `session_events` cho add/remove participant và create message
3. Thêm kiểm tra membership cơ bản
4. Viết test API

### Kết quả đầu ra
- session chat cơ bản dùng được

### Điều kiện hoàn thành
- 2 agent có thể tham gia session
- gửi message thường vào session thành công

---

## F11. Dựng CodexBridge process manager và JSON-RPC client
**Phụ thuộc:** F10  
**Mở khóa:** F12  
**File hoặc module chính:** `app/codex_bridge/process_manager.py`, `jsonrpc_client.py`, `models.py`

### Việc cần làm
1. Tạo process manager để start/stop `codex app-server`
2. Tạo JSON-RPC client gửi request và nhận response
3. Tạo các model request/response cơ bản
4. Tạo wrapper cho:
   - `initialize`
   - `thread/start`
   - `thread/resume`
   - `turn/start`
   - `turn/steer`
   - `turn/interrupt`
   - `thread/compact/start`
5. Viết integration smoke test

### Kết quả đầu ra
- Python code gọi được Codex app-server

### Điều kiện hoàn thành
- bridge hoạt động với runtime local thật hoặc mock đáng tin cậy

---

## F12. Tạo runtime service và session-thread mapping
**Phụ thuộc:** F11  
**Mở khóa:** F13  
**File hoặc module chính:** `app/services/runtime_service.py`, `app/services/thread_mapping.py`

### Việc cần làm
1. Tạo service quản lý runtime status
2. Tạo logic map agent trong session với thread Codex
3. Khi cần, tự tạo thread mới cho agent trong session
4. Lưu mapping này vào DB hoặc lớp state phù hợp
5. Thêm test cho create/reuse thread

### Kết quả đầu ra
- mỗi agent trong session có context Codex riêng

### Điều kiện hoàn thành
- cùng một agent vào cùng session không bị tạo thread mới vô tội vạ

---

## F13. Tạo message parser, mention router và job creation
**Phụ thuộc:** F12  
**Mở khóa:** F14  
**File hoặc module chính:** `app/services/message_parser.py`, `router.py`, `job_service.py`

### Việc cần làm
1. Parse message text để tìm:
   - mention `#agent`
   - command `/new`, `/interrupt`, `/compact`
2. Tạo `message_mentions`
3. Tạo job từ message có mention
4. Xác định target agent từ participant list
5. Viết test parser và router

### Kết quả đầu ra
- message có `#agent` tạo được job nội bộ

### Điều kiện hoàn thành
- `#builder sửa bug này` tạo đúng mention và job record

---

## F14. Tạo relay engine và command handlers
**Phụ thuộc:** F13  
**Mở khóa:** F15  
**File hoặc module chính:** `app/services/relay_engine.py`, `command_handler.py`, `permissions.py`

### Việc cần làm
1. Tạo relay engine gọi CodexBridge để thực thi job
2. Tạo command handler cho:
   - `/new`
   - `/interrupt`
   - `/compact`
3. Thêm lead/non-lead permission checks
4. Ghi `job_events`, `relay_edges`, `session_events`
5. Publish output đầu tiên của agent trở lại session dưới dạng message hệ thống hoặc agent message
6. Viết test integration cho mention và command flow

### Kết quả đầu ra
- luồng `#agent` từ message tới output hoạt động
- lead điều khiển được interrupt/compact

### Điều kiện hoàn thành
- end-to-end flow cơ bản pass

---

## F15. Presence, recovery, loop guard, artifacts, approval và streaming
**Phụ thuộc:** F14  
**Mở khóa:** F16  
**File hoặc module chính:** `app/services/presence.py`, `recovery.py`, `loop_guard.py`, `artifact_manager.py`, `streaming.py`, `approval_manager.py`

### Việc cần làm
1. Implement heartbeat endpoint và presence tracker
2. Đánh dấu online/offline từ `presence_heartbeats`
3. Thêm recovery service khi app restart
4. Tạo loop guard dựa trên `relay_edges`
5. Tạo artifact manager:
   - final text
   - diff
   - file metadata
6. Tạo approval manager và input-required handler tối thiểu
7. Implement:
   - `GET /api/v1/jobs/{job_id}`
   - `GET /api/v1/jobs/{job_id}/events`
   - `GET /api/v1/jobs/{job_id}/artifacts`
   - `POST /api/v1/jobs/{job_id}/cancel`
   - `POST /api/v1/jobs/{job_id}/resume`
   - `POST /api/v1/approvals/{approval_id}/accept`
   - `POST /api/v1/approvals/{approval_id}/decline`
   - `POST /api/v1/jobs/{job_id}/input`
   - `GET /api/v1/sessions/{session_id}/stream`
   - `GET /api/v1/jobs/{job_id}/stream`
8. Viết test cho các luồng này

### Kết quả đầu ra
- hệ thống vận hành ổn định hơn và output có cấu trúc

### Điều kiện hoàn thành
- presence cập nhật đúng
- recovery cơ bản hoạt động
- loop guard ngăn vòng lặp vô hạn
- job stream và artifact API dùng được

---

## F16. Hoàn thiện MVP, tài liệu và bề mặt A2A-ready
**Phụ thuộc:** F15  
**Mở khóa:** bàn giao MVP  
**File hoặc module chính:** `README.md`, `docs/`, `app/api/a2a_placeholder.py`

### Việc cần làm
1. Dọn API responses cho nhất quán
2. Thêm placeholder route:
   - `GET /.well-known/agent-card.json`
3. Viết mapping note từ session/job sang A2A task/artifact/status
4. Viết tài liệu chạy local
5. Viết tài liệu debug/troubleshooting
6. Thêm regression tests cho các luồng chính
7. Tạo seed/dev scripts
8. Chuẩn bị release notes cho MVP

### Kết quả đầu ra
- MVP có thể chạy, test và demo được

### Điều kiện hoàn thành
- clone repo, migrate DB, chạy app và thử luồng chính được theo README

---

## 5. Phụ thuộc chéo theo module

### API layer
- phụ thuộc repository layer
- phụ thuộc core config/error
- phụ thuộc services tương ứng

### Repository layer
- phụ thuộc DB connection và migrations

### Services layer
- `message_parser` phụ thuộc `messages repository`
- `router` phụ thuộc `participants repository` và `message_mentions repository`
- `job_service` phụ thuộc `jobs repository`
- `relay_engine` phụ thuộc `job_service`, `CodexBridge`, `artifact_manager`
- `command_handler` phụ thuộc `permissions`, `CodexBridge`, `job_service`
- `presence` phụ thuộc `presence repository`
- `recovery` phụ thuộc `jobs repository`, `runtime_service`, `thread_mapping`
- `loop_guard` phụ thuộc `relay_edges repository` và `jobs/session state`
- `approval_manager` phụ thuộc `approval repository`, `CodexBridge event translator`
- `artifact_manager` phụ thuộc `artifacts repository`, `job events`, `Codex outputs`

### CodexBridge layer
- phụ thuộc `core config`
- phụ thuộc `runtime_service`
- được dùng bởi `relay_engine`, `command_handler`, `recovery`, `approval_manager`

Không có module nào không có đầu vào hoặc đầu ra phụ thuộc.

---

## 6. Đề xuất thứ tự triển khai theo tuần hoặc sprint nhỏ

### Sprint 1
- F01
- F02
- F03

### Sprint 2
- F04
- F05
- F06

### Sprint 3
- F07
- F08
- F09

### Sprint 4
- F10
- F11
- F12

### Sprint 5
- F13
- F14

### Sprint 6
- F15
- F16

---

## 7. Definition of Done cho toàn MVP

MVP được xem là hoàn thành khi:

1. Có thể tạo session
2. Có thể đăng ký ít nhất 2 agent
3. Có thể cho 2 agent tham gia cùng một session
4. Có thể gửi message thường vào session
5. Có thể gửi `#agent` để tạo job thật
6. Agent phản hồi lại session qua coordinator
7. Lead dùng được `/interrupt` và `/compact`
8. Presence online/offline hoạt động ở mức cơ bản
9. Loop guard chặn vòng lặp relay quá dài
10. Job có artifact text tối thiểu, tốt hơn nếu có diff
11. Restart coordinator không làm mất hoàn toàn trạng thái chính
12. Có tài liệu để người khác chạy local và demo được

---

## 8. Ghi chú cuối

Nếu phải chọn giữa “thêm tính năng mới” và “làm chắc luồng hiện có”, hãy ưu tiên theo thứ tự này:

1. session và state đúng
2. mention routing đúng
3. CodexBridge ổn định
4. interrupt/compact đúng
5. artifacts và streaming
6. presence và recovery
7. A2A-ready surface

Khi hoàn tất F16, dự án sẽ có một coordinator local-first đủ dùng để cho nhiều Codex agent cộng tác trong một session chung, và đủ sạch để mở rộng dần sang A2A về sau.
