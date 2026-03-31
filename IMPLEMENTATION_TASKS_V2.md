# IMPLEMENTATION_TASKS_V2.md

# Danh sách nhiệm vụ triển khai sau MVP: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `PLAN_V2.md` thành backlog thực thi chi tiết cho phase sau MVP.

Khác với `IMPLEMENTATION_TASKS.md`:

- `IMPLEMENTATION_TASKS.md` chốt backlog F01-F16 để hoàn thành MVP
- `IMPLEMENTATION_TASKS_V2.md` chốt backlog **F17-F24** cho V2

Mỗi task trong tài liệu này được thiết kế để:

- vẫn đủ nhỏ để code trong một bước hoặc một PR gọn
- đủ rõ để tạo ra kết quả nhìn thấy được
- có phụ thuộc tuần tự rõ ràng
- mở rộng trên kiến trúc hiện tại mà không viết lại lõi coordinator

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
- **Mở khóa**
- **File hoặc module chính**
- **Việc cần làm**
- **Kết quả đầu ra**
- **Điều kiện hoàn thành**

### 2.3 Quy tắc phụ thuộc

- Không có task nào đứng một mình
- Mỗi task V2 nhận đầu vào từ task trước hoặc từ nền MVP đã có
- Nếu task cần schema, route hay service mới, phải ghi rõ nơi thay đổi

---

## 3. Sơ đồ phụ thuộc tổng thể

**F17 → F18 → F19 → F20 → F21 → F22 → F23 → F24**

Trong đó:

- F17: observability và diagnostics
- F18: channels/views
- F19: roles, permissions, participant policy
- F20: advanced jobs và offline queue
- F21: rules engine cơ bản
- F22: artifact improvements và transcript export
- F23: review mode và structured relay templates
- F24: phase presets và experimental A2A adapter bridge

---

## 4. Backlog chi tiết

## F17. Hoàn thiện system status, diagnostics và debug surface
**Phụ thuộc:** F16  
**Mở khóa:** F18  
**File hoặc module chính:** `app/api/system.py`, `app/services/system_status.py`, `app/services/debug_service.py`, `app/models/api/system.py`, `tests/integration/test_system_status.py`

### Việc cần làm
1. Hoàn thiện `GET /api/v1/system/status`
2. Thêm tổng hợp trạng thái cho:
   - DB
   - CodexBridge
   - active sessions
   - registered agents
   - queued/running jobs
   - pending approvals
3. Thêm internal debug surface hoặc route nhóm debug cho operator
4. Chuẩn hóa logging fields:
   - `session_id`
   - `agent_id`
   - `job_id`
   - `codex_thread_id`
   - `event_type`
5. Viết test cho status/diagnostics

### Kết quả đầu ra
- operator biết coordinator đang khỏe hay đang tắc ở đâu

### Điều kiện hoàn thành
- `system/status` phản ánh đúng health thực tế của coordinator
- có thể nhìn thấy queued jobs và pending approvals mà không đọc DB tay
- test route pass

---

## F18. Thêm channel hoặc view structure cho session
**Phụ thuộc:** F17  
**Mở khóa:** F19  
**File hoặc module chính:** `app/db/migrations/006_*.sql`, `app/repositories/channels.py`, `app/api/channels.py`, `app/services/channel_service.py`, `app/models/api/channels.py`

### Việc cần làm
1. Thiết kế model `session_channels` hoặc `session_views`
2. Thêm channel mặc định cho session mới:
   - `general`
   - `planning`
   - `review`
   - `debug`
3. Cho message/job/artifact gắn với channel hoặc view tương ứng
4. Thêm API để:
   - list channels
   - create channel
   - post message theo channel nếu policy cho phép
5. Viết test cho routing và listing theo channel

### Kết quả đầu ra
- session không còn chỉ là một transcript phẳng duy nhất

### Điều kiện hoàn thành
- session có ít nhất một channel mặc định hoạt động
- có thể gửi và lọc message theo channel/view
- test CRUD và API pass

---

## F19. Bổ sung roles, permissions và participant policy rõ hơn
**Phụ thuộc:** F18  
**Mở khóa:** F20  
**File hoặc module chính:** `app/services/permissions.py`, `app/services/participant_policy.py`, `app/api/participants.py`, `app/models/api/participants.py`, `tests/unit/test_permissions_v2.py`

### Việc cần làm
1. Mở rộng role model ở mức session participant:
   - `planner`
   - `builder`
   - `reviewer`
   - `researcher`
   - `tester`
2. Tách rõ default role của agent với role trong session
3. Bổ sung permission matrix cho:
   - relay
   - manual job creation
   - interrupt
   - compact
   - review-only actions
4. Thêm API cập nhật participant role/policy
5. Viết test permission cho lead và non-lead

### Kết quả đầu ra
- hành vi của từng participant rõ hơn và ít phụ thuộc suy luận từ text

### Điều kiện hoàn thành
- participant có role ở mức session
- command và relay checks dùng policy rõ ràng
- test permission pass cho các role chính

---

## F20. Nâng cấp advanced jobs và offline queue tối thiểu
**Phụ thuộc:** F19  
**Mở khóa:** F21  
**File hoặc module chính:** `app/db/migrations/007_*.sql`, `app/repositories/jobs.py`, `app/repositories/job_inputs.py`, `app/services/job_service.py`, `app/services/offline_queue.py`, `app/api/jobs.py`

### Việc cần làm
1. Implement:
   - `GET /api/v1/jobs`
   - `POST /api/v1/jobs`
   - `POST /api/v1/jobs/{job_id}/retry`
   - `POST /api/v1/jobs/{job_id}/resume`
2. Thêm bảng `job_inputs` hoặc cấu trúc normalized tương đương
3. Thêm offline queue tối thiểu cho agent offline
4. Khi agent online lại, coordinator có thể dispatch tiếp
5. Viết integration tests cho create/retry/resume/offline-queue

### Kết quả đầu ra
- job không còn chỉ là hệ quả của mention parser mà trở thành đơn vị điều phối mạnh hơn

### Điều kiện hoàn thành
- có thể tạo job trực tiếp qua API
- job failed/paused có thể retry hoặc resume theo contract rõ
- queue tối thiểu hoạt động khi agent offline

---

## F21. Tạo rules engine cơ bản và manual activation flow
**Phụ thuộc:** F20  
**Mở khóa:** F22  
**File hoặc module chính:** `app/db/migrations/008_*.sql`, `app/repositories/rules.py`, `app/services/rule_engine.py`, `app/api/rules.py`, `tests/integration/test_rules.py`

### Việc cần làm
1. Thêm bảng `rules`
2. Tạo rule model cơ bản:
   - relay rule
   - review-required rule
   - approval escalation rule
   - channel routing preference
3. Thêm API để:
   - create rule
   - list rules
   - activate/deactivate rule
4. Rule được evaluate trong service layer, không đẩy logic vào route
5. Viết test cho manual activation và rule evaluation cơ bản

### Kết quả đầu ra
- collaboration policy có thể cấu hình dần mà không sửa code tay cho từng session

### Điều kiện hoàn thành
- rule có thể được bật/tắt qua API
- ít nhất một flow relay hoặc review chịu tác động bởi rule
- test evaluation pass

---

## F22. Nâng cấp artifacts và transcript export
**Phụ thuộc:** F21  
**Mở khóa:** F23  
**File hoặc module chính:** `app/db/migrations/009_*.sql`, `app/services/artifact_manager.py`, `app/services/transcript_export.py`, `app/api/artifacts.py`, `app/api/sessions.py`

### Việc cần làm
1. Mở rộng artifact metadata:
   - file name
   - mime type
   - checksum
   - size
   - export metadata
2. Implement transcript export theo session
3. Implement session artifact listing tốt hơn
4. Nếu cần, thêm `attachments` hoặc export bundle cho review/handoff
5. Viết test cho transcript export và artifact metadata

### Kết quả đầu ra
- session/job có output dễ mang đi review, debug và handoff hơn

### Điều kiện hoàn thành
- transcript export tạo được artifact hoặc file export hợp lệ
- artifact metadata đủ để debug/download rõ ràng hơn
- test export pass

---

## F23. Tạo review mode và structured relay templates
**Phụ thuộc:** F22  
**Mở khóa:** F24  
**File hoặc module chính:** `app/services/review_mode.py`, `app/services/relay_templates.py`, `app/api/review.py`, `app/models/api/review.py`, `tests/integration/test_review_mode.py`

### Việc cần làm
1. Tạo review mode cho session hoặc job
2. Thêm relay templates:
   - planner → builder
   - builder → reviewer
   - reviewer → builder revise
3. Chuẩn hóa message/artifact types cho review
4. Tạo review summary artifact hoặc decision artifact
5. Viết integration tests cho builder-reviewer flow

### Kết quả đầu ra
- collaboration giữa builder và reviewer có flow rõ hơn thay vì chỉ dựa vào chat tự do

### Điều kiện hoàn thành
- một job builder có thể được chuyển sang reviewer bằng flow rõ ràng
- reviewer tạo được artifact hoặc decision có cấu trúc
- test review flow pass

---

## F24. Thêm phase presets và experimental A2A adapter bridge
**Phụ thuộc:** F23  
**Mở khóa:** kế hoạch V3  
**File hoặc module chính:** `app/db/migrations/010_*.sql`, `app/repositories/phases.py`, `app/services/phase_service.py`, `app/api/phases.py`, `app/api/a2a_adapter.py`, `docs/A2A_MAPPING.md`

### Việc cần làm
1. Thêm bảng `phases`
2. Tạo phase presets:
   - planning
   - implementation
   - review
   - revise
   - finalize
3. Cho session chọn active phase và dùng phase-aware relay template
4. Tạo experimental `A2AAdapter` layer riêng:
   - giữ internal model là `session/job/artifact`
   - map ra `task/status/artifact`
5. Nếu cần, thêm `a2a_tasks` mapping table
6. Viết test cho phase transition và adapter mapping cơ bản

### Kết quả đầu ra
- session có structured collaboration nhẹ
- public adapter bridge có đường đi rõ mà không làm bẩn Coordinator API

### Điều kiện hoàn thành
- session chuyển phase được
- relay có thể thay đổi theo phase preset
- adapter layer tồn tại riêng và map được ít nhất một job sang task model

---

## 5. Phụ thuộc chéo theo module

### API layer
- phụ thuộc repository layer
- phụ thuộc services tương ứng
- route mới không được chứa rule evaluation hoặc orchestration logic

### Repository layer
- phụ thuộc DB migrations mới cho:
  - channels/views
  - job_inputs
  - rules
  - attachments nếu có
  - phases
  - a2a_tasks nếu có

### Services layer
- `system_status` phụ thuộc repositories và CodexBridge health
- `channel_service` phụ thuộc messages, jobs, artifacts
- `participant_policy` phụ thuộc participants và permissions
- `offline_queue` phụ thuộc jobs và presence
- `rule_engine` phụ thuộc rules repository, relay engine và review mode
- `transcript_export` phụ thuộc messages, artifacts, jobs
- `review_mode` phụ thuộc relay templates, artifacts và jobs
- `phase_service` phụ thuộc phases, session state và relay templates
- `a2a_adapter` phụ thuộc jobs, artifacts, streaming model và phase state

### CodexBridge layer
- tiếp tục là execution engine duy nhất
- không bị gọi trực tiếp từ route mới; vẫn đi qua services

---

## 6. Đề xuất thứ tự triển khai theo sprint nhỏ

### Sprint 7
- F17
- F18

### Sprint 8
- F19
- F20

### Sprint 9
- F21
- F22

### Sprint 10
- F23
- F24

---

## 7. Definition of Done cho V2 foundation

V2 foundation được xem là hoàn thành khi:

1. Có `system/status` và debug surface hữu ích cho operator
2. Session có channel hoặc view structure rõ ràng
3. Participant có role/policy ở mức session
4. Có thể tạo job trực tiếp, retry và resume job
5. Agent offline có thể nhận queue tối thiểu và được dispatch lại khi online
6. Rule có thể được activate/deactivate qua API
7. Session có transcript export và artifact metadata tốt hơn
8. Builder-reviewer flow có review mode rõ ràng
9. Session có phase presets nhẹ
10. Có adapter bridge thử nghiệm cho A2A mà không phá internal model

---

## 8. Ghi chú cuối

Nếu phải chọn giữa:

- thêm public adapter sớm
- hay làm dày operator/review/job surface hiện có

hãy ưu tiên theo thứ tự:

1. observability
2. advanced jobs
3. artifacts/export
4. review mode
5. rules/roles
6. channels/views
7. phases
8. experimental A2A adapter

Khi hoàn tất F24, dự án sẽ có một nền V2 đủ chắc để tiếp tục sang V3 với A2A public API và orchestration nâng cao mà không phải viết lại lõi coordinator.
