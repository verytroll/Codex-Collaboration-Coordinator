# Danh sách nhiệm vụ triển khai giai đoạn V3: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `PLAN_V3.md` thành backlog thực thi chi tiết cho phase V3.

Khác với `IMPLEMENTATION_TASKS_V2.md`:

- `IMPLEMENTATION_TASKS_V2.md` chốt backlog **F17-F24** cho V2 foundation
- `IMPLEMENTATION_TASKS_V3.md` chốt backlog **F25-F31** cho V3

Mỗi task trong tài liệu này được thiết kế để:

- vẫn đủ nhỏ để code trong một bước hoặc một PR gọn
- có phụ thuộc tuần tự rõ ràng
- giữ internal model làm nguồn sự thật
- mở public/orchestration surface mà không viết lại lõi coordinator

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
- Mỗi task V3 nhận đầu vào từ task trước hoặc từ nền V2 đã có
- Nếu task thêm public surface mới, contract phải đi cùng test và docs

---

## 3. Sơ đồ phụ thuộc tổng thể

**F25 → F26 → F27 → F28 → F29 → F30 → F31**

Trong đó:

- F25: A2A public API v1
- F26: public subscribe/push event model
- F27: session templates và orchestration presets
- F28: advanced review orchestration và phase gates
- F29: runtime pools và isolated work contexts
- F30: operator dashboard/debug expansion
- F31: advanced policy engine và conditional automation

---

## 4. Backlog chi tiết

## F25. Chuẩn hóa A2A public API v1 trên nền adapter bridge
**Phụ thuộc:** F24  
**Mở khóa:** F26  
**File hoặc module chính:** `app/models/api/a2a_public.py`, `app/api/a2a_public.py`, `app/services/a2a_public_service.py`, `app/services/a2a_adapter.py`, `tests/integration/test_a2a_public_api.py`, `docs/A2A_PUBLIC_API.md`

### Việc cần làm
1. Chuẩn hóa public task resource model:
   - `task`
   - `task_status`
   - `task_artifact`
   - `task_error`
2. Tạo public routes tối thiểu:
   - `POST /api/v1/a2a/tasks`
   - `GET /api/v1/a2a/tasks`
   - `GET /api/v1/a2a/tasks/{task_id}`
3. Map rõ internal `session/job/artifact/phase` sang public task model
4. Chuẩn hóa public error/status mapping
5. Viết integration tests cho create/list/get và mapping cơ bản
6. Cập nhật docs contract public

### Kết quả đầu ra
- external client dùng được task API công khai mà không chạm Coordinator API nội bộ

### Điều kiện hoàn thành
- tạo được public task và thấy internal job/task mapping rõ
- public payload có version hoặc contract marker rõ ràng
- tests cho public task routes pass

---

## F26. Thêm public subscribe/push event model cho task
**Phụ thuộc:** F25  
**Mở khóa:** F27  
**File hoặc module chính:** `app/db/migrations/014_public_subscriptions.sql`, `app/repositories/public_subscriptions.py`, `app/repositories/public_events.py`, `app/services/public_event_stream.py`, `app/api/a2a_events.py`, `app/models/api/a2a_events.py`, `tests/integration/test_a2a_event_stream.py`

### Việc cần làm
1. Tạo subscription hoặc cursor model cho public event stream
2. Thêm task event types tối thiểu:
   - created
   - status_changed
   - artifact_attached
   - phase_changed
   - review_requested
   - completed
3. Implement public stream/subscribe routes
4. Hỗ trợ replay tối thiểu theo cursor hoặc `since`
5. Đảm bảo event payload không lộ internal-only fields
6. Viết integration tests cho subscribe/replay và ordering cơ bản

### Kết quả đầu ra
- client ngoài theo dõi task/status/artifact bằng stream rõ ràng thay vì polling thô

### Điều kiện hoàn thành
- có thể đọc event stream của task công khai
- event ordering và cursor/replay hoạt động ở mức cơ bản
- tests event stream pass

---

## F27. Tạo session templates và orchestration presets
**Phụ thuộc:** F26  
**Mở khóa:** F28  
**File hoặc module chính:** `app/db/migrations/015_session_templates.sql`, `app/repositories/session_templates.py`, `app/services/session_template_service.py`, `app/api/session_templates.py`, `app/models/api/session_templates.py`, `tests/integration/test_session_templates.py`

### Việc cần làm
1. Tạo model `session_templates`
2. Thêm templates mặc định:
   - `planning_heavy`
   - `implementation_review`
   - `research_review`
   - `hotfix_triage`
3. Cho template định nghĩa:
   - channels mặc định
   - participant roles
   - phase order
   - rule presets
4. Implement API để:
   - list templates
   - create template
   - instantiate session từ template
5. Viết tests cho template instantiation và preset application

### Kết quả đầu ra
- session có thể được khởi tạo theo preset collaboration lặp lại được

### Điều kiện hoàn thành
- session tạo từ template mang đúng channels/roles/phases/rules
- ít nhất một template mặc định hoạt động end-to-end
- tests template flow pass

---

## F28. Nâng cấp review orchestration và gated phase transitions
**Phụ thuộc:** F27  
**Mở khóa:** F29  
**File hoặc module chính:** `app/db/migrations/016_orchestration_runs.sql`, `app/services/orchestration_engine.py`, `app/services/phase_gate_service.py`, `app/services/review_mode.py`, `app/api/orchestration.py`, `app/models/api/orchestration.py`, `tests/integration/test_orchestration_v3.py`

### Việc cần làm
1. Tạo orchestration run hoặc state model tối thiểu
2. Thêm gated transitions:
   - review-required
   - approval-required
   - revise-on-reject
3. Tự động tạo handoff jobs/artifacts theo transition rules
4. Gắn decision artifacts rõ với phase transition
5. Chuẩn hóa builder → reviewer → builder revise → finalize flow
6. Viết integration tests cho orchestration flow có gate

### Kết quả đầu ra
- session/job có flow review và phase transition rõ hơn, bớt điều phối tay

### Điều kiện hoàn thành
- phase transition có thể bị chặn hoặc mở theo gate
- orchestration service tạo được handoff job/artifact đúng lúc
- tests orchestration pass

---

## F29. Thêm runtime pools và isolated work contexts
**Phụ thuộc:** F28  
**Mở khóa:** F30  
**File hoặc module chính:** `app/db/migrations/017_runtime_pools.sql`, `app/repositories/runtime_pools.py`, `app/repositories/work_contexts.py`, `app/services/runtime_pool_service.py`, `app/services/work_context_service.py`, `app/api/runtime_pools.py`, `tests/integration/test_runtime_pools.py`

### Việc cần làm
1. Tạo model `runtime_pools`
2. Tạo model `work_contexts` hoặc tương đương cho repo/worktree binding
3. Cho agent/job khai báo capability hoặc pool preference
4. Implement assignment logic và fallback tối thiểu
5. Thêm diagnostics cho pool utilization và context ownership
6. Viết tests cho assignment/recovery/fallback

### Kết quả đầu ra
- coordinator có thể chọn runtime/context phù hợp thay vì coi mọi execution là như nhau

### Điều kiện hoàn thành
- job có thể được gán vào pool/context theo policy cơ bản
- runtime failure có đường fallback hoặc recovery rõ
- tests runtime pool pass

---

## F30. Mở rộng operator dashboard/debug surface
**Phụ thuộc:** F29  
**Mở khóa:** F31  
**File hoặc module chính:** `app/services/operator_dashboard.py`, `app/services/debug_service.py`, `app/api/operator_dashboard.py`, `app/models/api/operator_dashboard.py`, `tests/integration/test_operator_dashboard.py`

### Việc cần làm
1. Tạo dashboard-ready aggregates cho:
   - queue heat
   - phase distribution
   - review bottlenecks
   - runtime pool health
   - public task throughput
2. Thêm route hoặc route group riêng cho operator dashboard
3. Chuẩn hóa filters theo session/template/phase/runtime pool
4. Đảm bảo aggregates đọc được từ repositories/services thay vì SQL rải rác trong API
5. Viết tests cho các aggregate chính

### Kết quả đầu ra
- operator có surface mạnh hơn để nhìn tắc nghẽn và trạng thái hệ thống

### Điều kiện hoàn thành
- có thể trả lời “đang tắc ở phase hay runtime nào” qua API
- dashboard aggregates đủ ổn định để làm nền cho UI sau này
- tests dashboard pass

---

## F31. Tạo advanced policy engine và conditional automation
**Phụ thuộc:** F30  
**Mở khóa:** roadmap xa hơn  
**File hoặc module chính:** `app/db/migrations/018_policy_conditions.sql`, `app/repositories/policies.py`, `app/services/policy_engine_v2.py`, `app/services/approval_manager.py`, `app/api/policies.py`, `app/models/api/policies.py`, `tests/integration/test_policy_engine_v2.py`

### Việc cần làm
1. Tạo policy model nâng cao:
   - conditional auto-approve
   - escalation policy
   - template-scoped policy
   - phase-scoped policy
2. Đánh giá policy trong service layer, không nhét logic vào route
3. Ghi audit trail rõ cho mỗi policy decision
4. Cho operator pause/resume automation nếu cần
5. Viết integration tests cho auto-approve/escalation/override

### Kết quả đầu ra
- automation có điều kiện rõ, giải thích được và ít phụ thuộc thao tác tay hơn

### Điều kiện hoàn thành
- ít nhất một flow approval/review chịu tác động bởi policy nâng cao
- operator thấy được vì sao policy đã quyết định như vậy
- tests policy engine v2 pass

---

## 5. Phụ thuộc chéo theo module

### API layer
- public A2A routes không được gọi trực tiếp vào repository nếu cần orchestration
- route mới phải đi qua service tương ứng
- operator surface không được tự nhúng policy hoặc assignment logic

### Repository layer
- phụ thuộc migrations mới cho:
  - public subscriptions/events
  - session templates
  - orchestration runs nếu có
  - runtime pools
  - work contexts
  - policy conditions

### Services layer
- `a2a_public_service` phụ thuộc `a2a_adapter`, jobs, artifacts, phases
- `public_event_stream` phụ thuộc session events, jobs, artifacts, reviews
- `session_template_service` phụ thuộc channels, participants, rules, phases
- `orchestration_engine` phụ thuộc phase service, review mode, relay templates, approvals
- `runtime_pool_service` phụ thuộc presence, jobs, runtime service
- `operator_dashboard` phụ thuộc system status, debug service, runtime pools, orchestration
- `policy_engine_v2` phụ thuộc rules hiện có, approvals, orchestration và runtime state

### CodexBridge layer
- tiếp tục là execution engine duy nhất
- không bị gọi trực tiếp từ public API mới; vẫn phải đi qua services
- runtime pools chỉ mở rộng cách gán/điều phối tới CodexBridge, không thay thế nó

---

## 6. Đề xuất thứ tự triển khai theo sprint nhỏ

### Sprint 11
- F25
- F26

### Sprint 12
- F27
- F28

### Sprint 13
- F29
- F30

### Sprint 14
- F31

---

## 7. Definition of Done cho V3 foundation

V3 foundation được xem là hoàn thành khi:

1. Có A2A public API v1 rõ ràng
2. Có public event stream hoặc subscribe/push model dùng được
3. Session có thể khởi tạo từ template
4. Phase transition có thể chịu gate/review/approval logic
5. Coordinator gán job vào runtime pool hoặc work context rõ ràng
6. Operator có dashboard-ready aggregates hữu ích
7. Policy automation nâng cao có audit trail và override cơ bản

---

## 8. Ghi chú cuối

Nếu phải chọn giữa:

- mở rộng dashboard/UI sớm
- hay khóa public API, event model và orchestration trước

hãy ưu tiên theo thứ tự:

1. A2A public API
2. public event model
3. session templates
4. orchestration gates
5. runtime pools
6. operator dashboard
7. advanced policy automation

Khi hoàn tất F31, dự án sẽ có một nền V3 đủ mạnh để tiến tiếp sang public collaboration surface lớn hơn, automation sâu hơn và execution scaling mà không phải phá vỡ lõi coordinator-first hiện tại.
