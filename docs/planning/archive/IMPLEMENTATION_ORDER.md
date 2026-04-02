# IMPLEMENTATION_ORDER.md

# Thứ tự triển khai theo PR: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/archive/IMPLEMENTATION_TASKS.md` thành **thứ tự triển khai thực chiến theo PR nhỏ**.

Khác với các tài liệu khác:

- `docs/planning/archive/PLAN.md` mô tả lộ trình cấp dự án
- `docs/planning/archive/IMPLEMENTATION_TASKS.md` mô tả backlog theo module
- `docs/planning/archive/IMPLEMENTATION_ORDER.md` mô tả **nên code cái gì trước, gộp thành PR nào, mỗi PR cần đạt gì**

Mục tiêu của tài liệu:

- giúp người mới biết **PR đầu tiên nên làm gì**
- giữ mỗi PR đủ nhỏ để review và sửa lỗi dễ
- đảm bảo PR sau luôn dựa trên PR trước
- tránh viết nhiều tính năng cùng lúc
- tạo ra các mốc demo rõ ràng

---

## 2. Nguyên tắc chia PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải để lại trạng thái hệ thống tốt hơn trước.**
3. **PR nào thêm tính năng cũng phải thêm test tối thiểu.**
4. **PR sau chỉ bắt đầu khi PR trước đã merge hoặc đã ổn định cục bộ.**
5. **Không gộp bridge, routing, presence, approval và streaming vào cùng một PR.**
6. **Ưu tiên dọc theo luồng dùng thật:** app chạy được → lưu state được → tạo session được → gửi message được → gọi Codex được → relay được.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR01 → PR02 → PR03 → PR04 → PR05 → PR06 → PR07 → PR08 → PR09 → PR10 → PR11 → PR12 → PR13 → PR14 → PR15 → PR16 → PR17 → PR18**

Không có PR nào bị cô lập:

- PR01 mở đường cho PR02
- PR18 phụ thuộc PR17
- mỗi PR ở giữa đều vừa nhận đầu vào từ PR trước, vừa mở khóa PR sau

---

## 4. Danh sách PR theo thứ tự triển khai

## PR01. Tạo skeleton repo và app chạy được
**Phụ thuộc:** không  
**Dựa trên tasks:** F01, một phần F02  
**Mục tiêu:** có bộ khung dự án và FastAPI app tối thiểu

### Bao gồm
- tạo cấu trúc thư mục theo `docs/reference/ARCHITECTURE.md`
- tạo `app/main.py`
- tạo route `GET /api/v1/healthz`
- tạo `README.md` dev setup ngắn
- thêm file môi trường mẫu

### Không bao gồm
- DB
- business logic
- CodexBridge

### Điều kiện merge
- app chạy local được
- `GET /api/v1/healthz` trả 200
- không có import loop rõ ràng

### Demo sau PR
- khởi động server và gọi healthcheck thành công

---

## PR02. Hoàn thiện toolchain và core app modules
**Phụ thuộc:** PR01  
**Dựa trên tasks:** phần còn lại của F02, F03  
**Mục tiêu:** có config, logging, error format, test/lint runner

### Bao gồm
- cấu hình dependencies
- cấu hình `pytest`
- cấu hình lint/format
- tạo `config.py`, `logging.py`, `errors.py`
- thêm request-id middleware
- tạo test đầu tiên

### Không bao gồm
- migration
- API business routes

### Điều kiện merge
- test chạy được
- lint chạy được
- error response có format thống nhất
- log có request id cơ bản

### Demo sau PR
- một route thành công và một route lỗi đều ra format dự kiến

---

## PR03. Thiết lập kết nối DB và migration framework
**Phụ thuộc:** PR02  
**Dựa trên tasks:** F04  
**Mục tiêu:** có thể khởi tạo SQLite và chạy migration lặp lại an toàn

### Bao gồm
- DB connection factory
- migration runner
- bảng version migrations
- test DB rỗng và migration idempotent cơ bản

### Không bao gồm
- bảng nghiệp vụ cụ thể
- repository

### Điều kiện merge
- migrate từ DB rỗng thành công
- migrate lần hai không phá DB

### Demo sau PR
- chạy lệnh migrate local thành công

---

## PR04. Tạo schema nhóm bảng nền
**Phụ thuộc:** PR03  
**Dựa trên tasks:** F05  
**Mục tiêu:** có các bảng nền cho coordinator

### Bao gồm
- `sessions`
- `agents`
- `agent_runtimes`
- `session_participants`
- index và ràng buộc cơ bản

### Không bao gồm
- message/job/artifact
- repository API

### Điều kiện merge
- migration pass từ đầu
- foreign key chính hoạt động

### Demo sau PR
- inspect DB thấy đủ bảng nền

---

## PR05. Tạo schema nhóm bảng runtime và lịch sử
**Phụ thuộc:** PR04  
**Dựa trên tasks:** F06  
**Mục tiêu:** có đầy đủ schema MVP để lưu message, job, artifact, approval, presence

### Bao gồm
- `messages`
- `message_mentions`
- `jobs`
- `job_events`
- `artifacts`
- `approval_requests`
- `presence_heartbeats`
- `relay_edges`
- `session_events`

### Không bao gồm
- business logic
- services

### Điều kiện merge
- full migration pass từ DB rỗng
- schema smoke test pass

### Demo sau PR
- DB có đầy đủ bảng MVP

---

## PR06. Repository layer cho session và agent
**Phụ thuộc:** PR05  
**Dựa trên tasks:** F07  
**Mục tiêu:** lưu và đọc được session, agent, participant

### Bao gồm
- session repository
- agent repository
- agent runtime repository
- participant repository
- CRUD tests

### Không bao gồm
- HTTP routes
- message/job repositories

### Điều kiện merge
- repository tests pass
- không có logic HTTP trộn trong repository

### Demo sau PR
- script nhỏ tạo session, agent, participant rồi đọc lại được

---

## PR07. Repository layer cho message, job, artifact, approval, presence
**Phụ thuộc:** PR06  
**Dựa trên tasks:** F08  
**Mục tiêu:** có đủ lớp truy cập dữ liệu cho phần runtime

### Bao gồm
- message repository
- mention repository
- job repository
- job event repository
- artifact repository
- approval repository
- presence repository
- relay edge repository

### Không bao gồm
- API routes
- business services

### Điều kiện merge
- CRUD tests pass cho các bảng runtime

### Demo sau PR
- script nhỏ tạo message và job rồi query lại được

---

## PR08. Session API và Agent API cơ bản
**Phụ thuộc:** PR07  
**Dựa trên tasks:** F09  
**Mục tiêu:** tạo và xem session/agent qua HTTP

### Bao gồm
- Pydantic models cho Session và Agent
- `POST /api/v1/sessions`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `PATCH /api/v1/sessions/{session_id}`
- `POST /api/v1/agents`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `PATCH /api/v1/agents/{agent_id}`
- route tests

### Không bao gồm
- participants
- messages

### Điều kiện merge
- API contract khớp `docs/reference/API.md`
- route tests pass

### Demo sau PR
- tạo session và agent bằng `curl`

---

## PR09. Participant API, Message API và session event log
**Phụ thuộc:** PR08  
**Dựa trên tasks:** F10  
**Mục tiêu:** có chat session cơ bản, chưa có mention relay

### Bao gồm
- `POST /api/v1/sessions/{session_id}/participants`
- `GET /api/v1/sessions/{session_id}/participants`
- `DELETE /api/v1/sessions/{session_id}/participants/{agent_id}`
- `POST /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/messages/{message_id}`
- ghi `session_events`
- membership checks cơ bản

### Không bao gồm
- parser `#agent`
- relay

### Điều kiện merge
- 2 agent tham gia session được
- gửi message thường thành công
- list messages hoạt động

### Demo sau PR
- demo một session có 2 agent và vài message thường

---

## PR10. Dựng CodexBridge process manager và JSON-RPC client
**Phụ thuộc:** PR09  
**Dựa trên tasks:** F11  
**Mục tiêu:** Python code gọi được Codex app-server

### Bao gồm
- process manager start/stop `codex app-server`
- JSON-RPC client
- request/response models cơ bản
- wrappers:
  - `initialize`
  - `thread/start`
  - `thread/resume`
  - `turn/start`
  - `turn/steer`
  - `turn/interrupt`
  - `thread/compact/start`
- integration smoke test

### Không bao gồm
- router mention
- session-thread mapping logic hoàn chỉnh

### Điều kiện merge
- bridge hoạt động với runtime local hoặc mock đủ tin cậy

### Demo sau PR
- script Python start Codex và gọi một turn đơn giản

---

## PR11. Runtime service và session-thread mapping
**Phụ thuộc:** PR10  
**Dựa trên tasks:** F12  
**Mục tiêu:** mỗi agent trong một session có context Codex ổn định

### Bao gồm
- runtime status service
- session-thread mapping service
- logic create/reuse thread cho agent trong session
- tests cho create/reuse

### Không bao gồm
- parser mention
- relay engine

### Điều kiện merge
- agent trong cùng session không bị tạo thread mới vô lý
- mapping lưu được và đọc lại được

### Demo sau PR
- cùng agent gửi hai lần trong cùng session dùng lại cùng thread

---

## PR12. Message parser, mention detection và job creation
**Phụ thuộc:** PR11  
**Dựa trên tasks:** F13  
**Mục tiêu:** message có `#agent` tạo được mention record và job record

### Bao gồm
- parser cho `#agent`
- parser cho `/new`, `/interrupt`, `/compact`
- lưu `message_mentions`
- tạo job từ mention
- router xác định target agent
- unit tests cho parser/router

### Không bao gồm
- gọi Codex thật
- command handlers hoàn chỉnh

### Điều kiện merge
- `#builder sửa bug này` tạo mention và job đúng

### Demo sau PR
- gửi message có mention và thấy DB có mention/job tương ứng

---

## PR13. Relay engine thực thi job qua CodexBridge
**Phụ thuộc:** PR12  
**Dựa trên tasks:** phần đầu F14  
**Mục tiêu:** từ mention tới phản hồi đầu tiên của agent

### Bao gồm
- relay engine lấy job và gọi CodexBridge
- ghi `job_events`
- ghi `relay_edges`
- publish output của agent về session dưới dạng message hệ thống hoặc agent message
- integration test cho `#agent`

### Không bao gồm
- `/interrupt`
- `/compact`
- permissions hoàn chỉnh

### Điều kiện merge
- end-to-end cơ bản pass: message mention → job → Codex → output quay lại session

### Demo sau PR
- `#builder tạo hello world` và thấy output quay lại session

---

## PR14. Command handlers và permissions lead/non-lead
**Phụ thuộc:** PR13  
**Dựa trên tasks:** phần còn lại F14  
**Mục tiêu:** thêm `/new`, `/interrupt`, `/compact` với permission rõ ràng

### Bao gồm
- command handler cho `/new`
- command handler cho `/interrupt`
- command handler cho `/compact`
- permission checks lead/non-lead
- ghi `session_events` và `job_events` phù hợp
- integration tests cho command flow

### Không bao gồm
- presence
- recovery
- artifacts nâng cao

### Điều kiện merge
- lead dùng command được
- non-lead bị chặn đúng nơi cần chặn

### Demo sau PR
- lead interrupt một job đang chạy thành công

---

## PR15. Presence và heartbeat
**Phụ thuộc:** PR14  
**Dựa trên tasks:** phần đầu F15  
**Mục tiêu:** biết agent online/offline ở mức cơ bản

### Bao gồm
- heartbeat endpoint
- presence tracker
- cập nhật `presence_heartbeats`
- logic online/offline cơ bản
- tests cho presence

### Không bao gồm
- recovery
- loop guard
- artifact manager

### Điều kiện merge
- trạng thái online/offline cập nhật đúng theo heartbeat

### Demo sau PR
- agent gửi heartbeat và xuất hiện online trong API/DB

---

## PR16. Recovery và loop guard
**Phụ thuộc:** PR15  
**Dựa trên tasks:** phần giữa F15  
**Mục tiêu:** giảm tình trạng treo và relay vô hạn

### Bao gồm
- recovery service khi app restart
- loop guard dùng `relay_edges`
- policy dừng loop để chờ con người can thiệp
- tests cho restart/recovery và loop detection

### Không bao gồm
- artifacts
- approvals
- SSE streaming

### Điều kiện merge
- loop đơn giản bị chặn
- job dang dở có hướng recovery cơ bản

### Demo sau PR
- mô phỏng 2 agent nhắc qua nhắc lại và hệ thống chặn đúng lúc

---

## PR17. Artifact manager, approval/input-required và streaming
**Phụ thuộc:** PR16  
**Dựa trên tasks:** phần còn lại F15  
**Mục tiêu:** output có cấu trúc và có thể theo dõi theo thời gian thực

### Bao gồm
- artifact manager cho:
  - final text
  - diff
  - file metadata
- approval manager
- input-required handler tối thiểu
- routes:
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
- tests cho job detail, artifact, approval, streaming

### Không bao gồm
- A2A public API hoàn chỉnh
- dashboard lớn

### Điều kiện merge
- output có artifact cơ bản
- stream dùng được
- approval/input flow không bị treo vô hạn

### Demo sau PR
- theo dõi stream của một job đang chạy và xem artifact sau khi xong

---

## PR18. Hoàn thiện MVP, docs và A2A-ready surface
**Phụ thuộc:** PR17  
**Dựa trên tasks:** F16  
**Mục tiêu:** khóa chất lượng bản MVP và chừa sẵn đường mở rộng A2A

### Bao gồm
- dọn response models cho nhất quán
- `GET /.well-known/agent-card.json` placeholder
- note mapping session/job sang A2A task/artifact/status
- tài liệu chạy local
- troubleshooting guide
- regression tests cho luồng chính
- seed/dev scripts
- release notes MVP

### Không bao gồm
- A2A implementation đầy đủ
- auth production-grade

### Điều kiện merge
- clone repo, migrate DB, chạy app và demo luồng chính được theo README
- regression tests pass

### Demo sau PR
- demo toàn bộ luồng chính từ tạo session tới relay agent, interrupt, stream và artifact

---

## 5. Mốc demo quan trọng

### Mốc A — sau PR02
Bạn có:
- app chạy được
- test/lint chạy được
- core config ổn

### Mốc B — sau PR05
Bạn có:
- schema DB MVP đầy đủ
- có thể bắt đầu code repository nghiêm túc

### Mốc C — sau PR09
Bạn có:
- coordinator API cơ bản dùng được
- tạo session, agent, participant, message qua HTTP

### Mốc D — sau PR13
Bạn có:
- luồng `#agent` đầu-cuối đầu tiên
- agent có thể trả lời vào session

### Mốc E — sau PR17
Bạn có:
- MVP kỹ thuật gần hoàn chỉnh
- presence, recovery, loop guard, artifact, approval, streaming

### Mốc F — sau PR18
Bạn có:
- bản MVP có thể demo và bàn giao nội bộ

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:

- `pr/01-skeleton`
- `pr/02-core-toolchain`
- `pr/03-migrations`
- `pr/04-base-schema`
- `pr/05-runtime-schema`
- `pr/06-session-agent-repositories`
- `pr/07-runtime-repositories`
- `pr/08-session-agent-api`
- `pr/09-participants-messages-api`
- `pr/10-codex-bridge`
- `pr/11-thread-mapping`
- `pr/12-parser-and-jobs`
- `pr/13-relay-engine`
- `pr/14-commands-and-permissions`
- `pr/15-presence`
- `pr/16-recovery-and-loop-guard`
- `pr/17-artifacts-approval-streaming`
- `pr/18-mvp-polish`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:

- code chạy được local
- test mới pass
- test cũ không vỡ
- README hoặc docs liên quan đã cập nhật
- không thêm dead code rõ ràng
- không mở rộng phạm vi PR quá đà
- có ít nhất một cách demo thủ công

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự PR01 → PR18
- không nhảy qua PR sau nếu PR trước chưa ổn

Nếu bạn làm theo sprint:
- gộp 2–3 PR nhỏ thành một sprint nội bộ
- nhưng vẫn giữ commit và review theo PR nhỏ

Nếu bạn dùng cùng `docs/planning/archive/IMPLEMENTATION_TASKS.md`:
- `docs/planning/archive/IMPLEMENTATION_TASKS.md` trả lời câu hỏi: **phải code module nào**
- `docs/planning/archive/IMPLEMENTATION_ORDER.md` trả lời câu hỏi: **nên merge theo thứ tự nào**

Tài liệu này là cây cầu nối từ kế hoạch sang hành động thực tế.
