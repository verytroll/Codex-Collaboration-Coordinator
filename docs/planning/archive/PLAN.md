# PLAN.md

# Kế hoạch phát triển dự án: Codex Collaboration Coordinator

## 1. Mục tiêu của kế hoạch

Tài liệu này cập nhật lại kế hoạch triển khai theo các tài liệu mới nhất:

- `docs/reference/BORROWED_IDEAS.md`
- `docs/reference/PRD.md`
- `docs/reference/ARCHITECTURE.md`
- `docs/reference/API.md`
- `docs/reference/DB_SCHEMA.md`

Mục tiêu của bản kế hoạch mới là chuyển trọng tâm từ **A2A adapter thuần túy** sang một hệ thống **coordinator-first, CodexBridge-backed, local-first**, có thể:

- điều phối nhiều Codex agent trong cùng một session
- hỗ trợ giao việc bằng `#agent`
- quản lý lead / non-lead
- hỗ trợ `/new`, `/interrupt`, `/compact`
- lưu trạng thái bền để phục hồi sau restart
- theo dõi presence cơ bản
- ngăn relay loop
- tạo artifact tối thiểu
- chừa đường mở rộng sang A2A ở giai đoạn sau

---

## 2. Phạm vi của bản đầu

### 2.1 Phạm vi MVP

Bản đầu cần hoàn thành được các khả năng sau:

1. Tạo session và lưu bền vào SQLite
2. Đăng ký agent và runtime Codex
3. Cho agent tham gia session
4. Gửi message vào session
5. Parse mention `#agent`
6. Tạo job nội bộ từ mention
7. Gọi Codex qua `CodexBridge`
8. Đưa output của agent trở lại session
9. Hỗ trợ `/interrupt`
10. Hỗ trợ `/compact`
11. Theo dõi heartbeat và online/offline cơ bản
12. Chặn relay loop ở mức tối thiểu
13. Lưu artifact text, diff và file metadata cơ bản
14. Có API HTTP và SSE đủ dùng cho local development

### 2.2 Chưa làm trong MVP

Các phần dưới đây không phải trọng tâm của bản đầu:

- auth production-grade
- multi-tenant
- dashboard lớn
- cloud deployment hoàn chỉnh
- phase engine đầy đủ
- rules engine đầy đủ
- jobs nâng cao với workflow templates
- A2A public API hoàn chỉnh

---

## 3. Nguyên tắc triển khai

1. **Coordinator-first**: mọi hành động đi qua coordinator, agent không nói chuyện trực tiếp với nhau.
2. **Codex là execution engine**: không fork Codex ở giai đoạn đầu.
3. **State-first**: mỗi hành động quan trọng phải được ghi DB và event log trước khi phát ra ngoài.
4. **Mỗi bước có thể chạy thử ngay**: không gộp nhiều thay đổi lớn vào cùng một task.
5. **Test đi cùng tính năng**: route mới, repository mới, mapper mới đều cần test tối thiểu.
6. **Tăng độ phức tạp dần**: từ session/message cơ bản, đến mention routing, rồi mới tới relay loop, approval và artifacts.
7. **Giữ đường nâng cấp**: API và schema phải đủ sạch để nối sang A2A ở giai đoạn sau.

---

## 4. Trình tự triển khai cấp cao

Dự án sẽ đi qua 8 giai đoạn tuần tự:

**G01 → G02 → G03 → G04 → G05 → G06 → G07 → G08**

Trong đó:

- **G01** tạo nền tảng repo, app và test
- **G02** dựng state store và schema
- **G03** dựng coordinator API cơ bản
- **G04** dựng CodexBridge và runtime integration
- **G05** bật mention routing và relay engine
- **G06** thêm control commands, presence và recovery
- **G07** hoàn thiện artifact, streaming và ổn định hóa
- **G08** chuẩn bị mở rộng A2A và đóng gói MVP

Không có giai đoạn nào độc lập:

- G02 phụ thuộc G01
- G03 phụ thuộc G02
- G04 phụ thuộc G03
- G05 phụ thuộc G04
- G06 phụ thuộc G05
- G07 phụ thuộc G06
- G08 phụ thuộc G07

---

## 5. Kế hoạch chi tiết theo giai đoạn

## G01. Thiết lập nền tảng dự án
**Phụ thuộc:** không  
**Mở khóa:** G02  
**Kết quả:** có repo, app skeleton, cấu trúc thư mục, công cụ dev và test cơ bản

### Công việc
1. Tạo repo và cấu trúc thư mục theo `docs/reference/ARCHITECTURE.md`
2. Tạo FastAPI app skeleton
3. Cấu hình Python environment, lint, formatter, test runner
4. Tạo `GET /api/v1/healthz`
5. Tạo logging tối thiểu
6. Viết README cách chạy local

### Tiêu chí xong
- app chạy được
- test healthz pass
- cấu trúc thư mục ổn định

---

## G02. Dựng cơ sở dữ liệu và lớp lưu trữ trạng thái
**Phụ thuộc:** G01  
**Mở khóa:** G03  
**Kết quả:** có migration, repository và các model DB tối thiểu theo `docs/reference/DB_SCHEMA.md`

### Công việc
1. Tạo migration framework đơn giản
2. Tạo các bảng MVP:
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
   - `presence_heartbeats`
   - `relay_edges`
   - `session_events`
3. Tạo repository layer cho từng nhóm bảng
4. Tạo DB test fixtures
5. Viết test CRUD quan trọng

### Tiêu chí xong
- migration chạy được từ đầu
- có thể tạo session, agent, participant, message, job bằng code
- repository test pass

---

## G03. Dựng Coordinator API cơ bản
**Phụ thuộc:** G02  
**Mở khóa:** G04  
**Kết quả:** người dùng có thể tạo session, đăng ký agent, thêm participant, gửi message và xem lại lịch sử

### Công việc
1. Implement Session API cơ bản
2. Implement Agent Registry API cơ bản
3. Implement Session Participant API
4. Implement Message API cơ bản
5. Thêm validation và error response thống nhất
6. Thêm SSE session stream khung ban đầu
7. Ghi `session_events` cho các hành động chính

### Tiêu chí xong
- có thể tạo session
- có thể thêm 2 agent vào session
- có thể gửi chat thường vào session
- có thể xem lại danh sách message

---

## G04. Dựng CodexBridge và runtime integration
**Phụ thuộc:** G03  
**Mở khóa:** G05  
**Kết quả:** coordinator có thể gọi Codex app-server để tạo thread, start turn, interrupt và compact

### Công việc
1. Tạo process manager cho `codex app-server`
2. Tạo JSON-RPC client
3. Tạo wrapper method cho các primitive cần thiết:
   - `initialize`
   - `thread/start`
   - `thread/resume`
   - `turn/start`
   - `turn/steer`
   - `turn/interrupt`
   - `thread/compact/start`
4. Tạo event translator nhận stream từ Codex
5. Map runtime status sang DB
6. Viết integration test với một runtime local

### Tiêu chí xong
- coordinator gọi được Codex bằng code
- có thể tạo thread cho agent
- có thể bắt đầu một turn đơn giản

---

## G05. Bật mention routing và relay engine
**Phụ thuộc:** G04  
**Mở khóa:** G06  
**Kết quả:** message chứa `#agent` tạo job, gọi đúng agent đích và publish phản hồi trở lại session

### Công việc
1. Tạo parser phát hiện mention và command
2. Tạo `message_mentions` khi có `#agent`
3. Tạo job nội bộ từ message có mention
4. Tạo router để xác định target agent
5. Tạo session-thread mapping cho agent trong session
6. Gọi CodexBridge để thực thi job
7. Lưu `job_events` và publish output vào session
8. Tạo `relay_edges` khi agent A gọi agent B
9. Hỗ trợ luồng agent gọi agent khác qua coordinator

### Tiêu chí xong
- `#builder ...` tạo job thật
- builder phản hồi lại session
- có trace job và relay trong DB

---

## G06. Thêm control commands, presence và recovery
**Phụ thuộc:** G05  
**Mở khóa:** G07  
**Kết quả:** hệ thống điều khiển được phiên cộng tác và bớt mong manh khi runtime hoặc app khởi động lại

### Công việc
1. Implement `/new`
2. Implement `/interrupt`
3. Implement `/compact`
4. Implement heartbeat endpoint và presence tracker
5. Đánh dấu online/offline theo timeout
6. Hỗ trợ offline queue tối thiểu cho agent không online
7. Bổ sung recovery khi coordinator restart:
   - nạp lại session đang mở
   - nạp lại job chưa terminal
   - đồng bộ lại runtime status nếu có thể
8. Ghi audit event cho command và recovery

### Tiêu chí xong
- lead dùng được `/interrupt` và `/compact`
- presence hiển thị đúng online/offline cơ bản
- restart coordinator không làm mất session và job state

---

## G07. Hoàn thiện artifact, streaming, loop guard và approval/input
**Phụ thuộc:** G06  
**Mở khóa:** G08  
**Kết quả:** output của agent có cấu trúc rõ ràng, hệ thống có kiểm soát vòng lặp và xử lý được các luồng chờ tương tác

### Công việc
1. Tạo artifact manager
2. Ghi final text artifact
3. Ghi diff artifact
4. Ghi file metadata hoặc file export tối thiểu
5. Hoàn thiện job stream SSE
6. Implement approval flow tối thiểu
7. Implement input-required flow tối thiểu
8. Implement loop guard:
   - đếm relay hops
   - tạm dừng job/session khi vượt ngưỡng
   - yêu cầu xác nhận để tiếp tục
9. Viết test cho các luồng này

### Tiêu chí xong
- job có artifact rõ ràng
- stream session và stream job dùng được
- relay loop không chạy vô hạn
- approval/input-required không làm hệ thống treo vô thời hạn

---

## G08. Chuẩn bị mở rộng A2A và đóng gói MVP
**Phụ thuộc:** G07  
**Mở khóa:** bàn giao MVP  
**Kết quả:** có tài liệu, test, script chạy local và bề mặt mở rộng sang A2A

### Công việc
1. Dọn sạch API responses và model names
2. Chốt mapping session/job/artifact sang A2A task/artifact/status
3. Thêm `/.well-known/agent-card.json` dạng placeholder cho phase sau
4. Viết test regression cho các luồng chính
5. Viết tài liệu sử dụng local
6. Viết tài liệu debug/troubleshooting
7. Chuẩn hóa seed data/dev scripts
8. Đóng tag bản MVP

### Tiêu chí xong
- clone repo là chạy local được
- có tài liệu đủ cho người khác test MVP
- A2A có đường nối rõ cho phase tiếp theo

---

## 6. Danh sách phụ thuộc chi tiết

### 6.1 Phụ thuộc giữa các giai đoạn

- **G01 → G02**: chưa có app và toolchain thì chưa làm migration và repository
- **G02 → G03**: chưa có DB thì API session/agent/message không có nơi lưu
- **G03 → G04**: cần API và state store trước khi gắn runtime thật
- **G04 → G05**: cần CodexBridge trước khi mention tạo job thực thi thật
- **G05 → G06**: cần mention/job hoạt động trước khi thêm interrupt/compact/recovery
- **G06 → G07**: cần phiên tương tác ổn định trước khi thêm artifact/approval/loop guard
- **G07 → G08**: cần MVP đủ tính năng trước khi đóng gói tài liệu và chuẩn hóa A2A

### 6.2 Phụ thuộc giữa các khối chức năng

- **Session API** phụ thuộc **sessions repository**
- **Agent Registry API** phụ thuộc **agents repository** và **agent_runtimes repository**
- **Participant API** phụ thuộc **sessions** và **agents**
- **Message API** phụ thuộc **messages repository** và **session membership checks**
- **Mention Router** phụ thuộc **message parsing**, **participant lookup** và **jobs repository**
- **Relay Engine** phụ thuộc **Mention Router**, **CodexBridge** và **job_events**
- **Command Handler** phụ thuộc **lead permission checks** và **CodexBridge**
- **Presence Tracker** phụ thuộc **heartbeat endpoint** và **presence_heartbeats**
- **Artifact Manager** phụ thuộc **Codex event translator** và **artifacts repository**
- **Loop Guard** phụ thuộc **relay_edges** và **job/session state update**
- **Approval Manager** phụ thuộc **Codex event translator**, **approval_requests** và **job control endpoints**
- **A2A-ready layer** phụ thuộc **job state model**, **artifact model** và **streaming model**

Không có khối chức năng nào bị cô lập.

---

## 7. Mốc bàn giao quan trọng

### Mốc M1 — App khung chạy được
Đạt sau G01.

### Mốc M2 — Có state store thật
Đạt sau G02.

### Mốc M3 — Chat session cơ bản hoạt động
Đạt sau G03.

### Mốc M4 — Coordinator gọi được Codex thật
Đạt sau G04.

### Mốc M5 — Mention-based collaboration hoạt động
Đạt sau G05.

### Mốc M6 — Phiên cộng tác điều khiển được
Đạt sau G06.

### Mốc M7 — Output và streaming đủ dùng
Đạt sau G07.

### Mốc M8 — MVP hoàn chỉnh và có thể chia sẻ
Đạt sau G08.

---

## 8. Cách làm việc được khuyến nghị

### 8.1 Cỡ thay đổi cho mỗi PR
Mỗi PR nên chỉ làm một trong các nhóm sau:

- một migration
- một repository
- một API route group nhỏ
- một parser/router rule
- một command handler
- một event mapper
- một test suite nhỏ

### 8.2 Quy tắc “xong” cho từng task nhỏ
Một task nhỏ được xem là xong khi có đủ:

1. code chạy được
2. test liên quan pass
3. log hoặc error handling tối thiểu
4. tài liệu hoặc comment ngắn được cập nhật

### 8.3 Thứ tự ưu tiên khi thiếu thời gian
Nếu cần cắt phạm vi, hãy giữ thứ tự ưu tiên này:

1. session
2. agents
3. participants
4. messages
5. mention routing
6. CodexBridge
7. `/interrupt`
8. `/compact`
9. artifacts text
10. SSE
11. presence
12. loop guard
13. approval/input-required
14. A2A placeholder

---

## 9. Kế hoạch sau MVP

### V2
- channels hoặc views nâng cao
- rules engine cơ bản
- jobs nâng cao
- review mode
- export transcript tốt hơn
- file artifacts hoàn chỉnh hơn

### V3
- structured phases
- session templates
- A2A public API hoàn chỉnh
- dashboard quan sát và debug
- deploy nhiều runtime/host

---

## 10. Kết luận

Bản kế hoạch mới chốt dự án theo hướng:

- **coordinator-first**
- **Codex là execution engine phía sau**
- **state được lưu bền và event-driven**
- **trải nghiệm cộng tác mượn từ `codex-weave`**
- **kiến trúc điều phối mượn từ `agentchattr`**
- **A2A là hướng mở rộng, không phải trọng tâm của MVP**

Từ đây, tài liệu phù hợp để bắt đầu code ngay là `docs/planning/archive/IMPLEMENTATION_TASKS.md`.
