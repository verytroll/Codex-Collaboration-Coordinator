# Danh sách nhiệm vụ triển khai giai đoạn V4: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `PLAN_V4.md` thành backlog thực thi chi tiết cho phase V4.

Khác với `IMPLEMENTATION_TASKS_V3.md`:

- `IMPLEMENTATION_TASKS_V3.md` chốt backlog **F25-F31** cho V3 foundation
- `IMPLEMENTATION_TASKS_V4.md` chốt backlog **F32-F35** cho V4 hardening, telemetry, release readiness và deployment readiness

Mỗi task trong tài liệu này được thiết kế để:

- đủ nhỏ để có thể code và review theo một feature slice rõ
- có phụ thuộc tuần tự rõ ràng giữa reliability, observability, release và deployment
- giữ coordinator-first architecture làm trung tâm
- ưu tiên hardening, đo lường và vận hành trước khi mở thêm UI hoặc feature surface lớn

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

- Không có task V4 nào đứng riêng lẻ
- Mỗi task V4 nhận đầu vào từ task trước hoặc từ nền V3 đã có
- Nếu task thêm diagnostics, telemetry hoặc deployment surface mới, tài liệu và test liên quan phải đi cùng

---

## 3. Sơ đồ phụ thuộc tổng thể

**F32 → F33 → F34 → F35**

Trong đó:

- F32: hardening và reliability
- F33: telemetry và observability
- F34: release readiness và operational safety
- F35: deployment surface và external readiness

---

## 4. Backlog chi tiết

## F32. Hardening và reliability cho public/orchestration/runtime surface
**Phụ thuộc:** F31  
**Mở khóa:** F33  
**File hoặc module chính:** `app/core/errors.py`, `app/api/dependencies.py`, `app/services/a2a_public_service.py`, `app/services/public_event_stream.py`, `app/services/orchestration_engine.py`, `app/services/runtime_pool_service.py`, `app/services/policy_engine_v2.py`, `app/codex_bridge/process_manager.py`, `tests/integration/test_reliability_hardening.py`, `docs/TROUBLESHOOTING.md`

### Việc cần làm
1. Rà soát validation và error mapping cho:
   - A2A public task routes
   - public event replay/cursor
   - session template instantiation
   - orchestration decisions và phase transitions
   - policy/operator actions
2. Thêm guard cho duplicate action và idempotency tối thiểu ở các flow dễ bị retry:
   - create task
   - retry/resume/requeue
   - review decision
   - phase transition
   - interrupt
3. Làm rõ timeout, cancellation, cleanup và fallback boundaries quanh CodexBridge, runtime pools và work contexts
4. Chuẩn hóa startup checks, migration safety và backward-compatible defaults cho các route/service nhạy cảm
5. Viết integration tests cho edge cases, failure paths, replay/retry paths và recovery paths
6. Cập nhật troubleshooting notes cho các failure mode chính

### Kết quả đầu ra
- các flow quan trọng fail có kiểm soát hơn, ít tạo duplicate state hoặc side effect mơ hồ hơn

### Điều kiện hoàn thành
- lỗi trả về có loại và thông điệp nhất quán hơn ở các surface chính
- retry/replay không tạo duplicate state khó giải thích ở mức cơ bản
- bridge/runtime failure có đường fallback hoặc cleanup rõ ràng
- tests hardening/recovery pass

---

## F33. Thêm telemetry và observability theo thời gian
**Phụ thuộc:** F32  
**Mở khóa:** F34  
**File hoặc module chính:** `app/core/logging.py`, `app/core/middleware.py`, `app/services/system_status.py`, `app/services/debug_service.py`, `app/services/operator_dashboard.py`, `app/services/public_event_stream.py`, `app/services/runtime_pool_service.py`, `app/codex_bridge/process_manager.py`, `app/models/api/system.py`, `app/models/api/operator_dashboard.py`, `app/api/system.py`, `app/api/operator_dashboard.py`, `tests/integration/test_system_telemetry.py`, `docs/OBSERVABILITY.md`

### Việc cần làm
1. Chuẩn hóa structured logging với correlation IDs hoặc request IDs cho:
   - API request
   - session
   - agent
   - job
   - phase
   - review
   - runtime assignment
   - public task/event flows
2. Bổ sung metrics hoặc telemetry counters tối thiểu cho:
   - queue depth
   - job latency
   - phase duration
   - review bottlenecks
   - runtime pool health
   - CodexBridge error rates
   - public task/event throughput
3. Tách aggregate health với live/recent telemetry trong `system/status` hoặc diagnostics surface
4. Mở rộng operator/debug surface để trả lời:
   - đang chậm ở đâu
   - đang fail ở đâu
   - phase/runtime nào đang tắc
5. Viết tests cho correlation, telemetry aggregation và telemetry-facing APIs
6. Viết docs về semantics của logs, metrics và telemetry views

### Kết quả đầu ra
- hệ thống có telemetry surface đủ rõ để phân biệt aggregate health với recent/live behavior

### Điều kiện hoàn thành
- có thể truy vết một flow từ request sang job/phase/runtime bằng correlation ID
- telemetry surface trả lời được bottleneck hoặc failure hotspot cơ bản
- CodexBridge health không còn chỉ là aggregate snapshot
- tests telemetry pass

---

## F34. Release readiness và operational safety
**Phụ thuộc:** F33  
**Mở khóa:** F35  
**File hoặc module chính:** `scripts/test.ps1`, `scripts/lint.ps1`, `scripts/smoke.ps1`, `scripts/dev.ps1`, `app/db/migrations/runner.py`, `docs/LOCAL_SETUP.md`, `docs/TROUBLESHOOTING.md`, `docs/RELEASE_NOTES_V3.md`, `docs/RUNBOOK.md`, `README.md`, `STATUS.md`

### Việc cần làm
1. Chốt release checklist tối thiểu cho release candidate:
   - `pytest`
   - lint
   - smoke test
   - migration verification
   - seed/reset verification
2. Chuẩn hóa scripts hoặc command path để release checklist chạy lặp lại được
3. Viết runbook vận hành cho:
   - startup local/dev
   - startup prod-like tối thiểu
   - incident triage
   - backup/restore SQLite
   - recovery sau runtime/CodexBridge failure
4. Chuẩn hóa env var docs, config profile notes và safe defaults theo môi trường
5. Cập nhật release notes, upgrade notes, README, STATUS và tài liệu vận hành cho nhất quán
6. Viết acceptance hoặc smoke tests đại diện cho release gate tối thiểu

### Kết quả đầu ra
- có release discipline rõ hơn thay vì chỉ dựa vào thao tác tay và trí nhớ tác giả

### Điều kiện hoàn thành
- có thể dựng release candidate theo checklist lặp lại được
- runbook đủ để người khác startup, debug và recovery ở mức cơ bản
- release docs và operational docs đồng bộ với trạng thái hệ thống
- smoke/release gate pass

---

## F35. Deployment surface và external readiness tối thiểu
**Phụ thuộc:** F34  
**Mở khóa:** roadmap xa hơn  
**File hoặc module chính:** `app/core/config.py`, `app/main.py`, `app/api/health.py`, `scripts/run.ps1`, `scripts/dev.ps1`, `Dockerfile`, `.dockerignore`, `docs/DEPLOYMENT.md`, `tests/integration/test_deployment_readiness.py`

### Việc cần làm
1. Chuẩn hóa deployment profile tối thiểu:
   - packaging/runtime profile
   - startup/readiness checks
   - migration strategy khi boot
2. Thêm guardrails tối thiểu cho môi trường ngoài local:
   - config-based access boundaries
   - safer defaults
   - rate limiting hoặc quota guardrails nhẹ nếu cần
3. Đảm bảo health/readiness endpoints và startup path phản ánh đúng trạng thái dependencies chính
4. Viết docs topology triển khai tối thiểu, env requirements và operational assumptions
5. Nếu cần, thêm containerization hoặc script đóng gói tối thiểu để chạy được ngoài local
6. Viết tests hoặc smoke checks cho deployment readiness path

### Kết quả đầu ra
- coordinator có surface triển khai tối thiểu rõ ràng hơn, đủ an toàn để mang ra môi trường ngoài local

### Điều kiện hoàn thành
- có ít nhất một deployment profile được mô tả và verify ở mức cơ bản
- startup/readiness contract rõ ràng hơn cho môi trường ngoài local
- deployment docs và smoke/deployment checks pass

---

## 5. Phụ thuộc chéo theo module

### API layer
- hardening không được đẩy logic xử lý lỗi hoặc retry xuống route một cách rải rác
- telemetry-facing routes phải đi qua service/read model rõ ràng thay vì đọc state chắp vá trong API
- health/readiness surfaces phải phản ánh service/repository/runtime state thật

### Repository layer
- nếu telemetry hoặc reliability cần state mới, phải thêm repository/migration tương ứng thay vì nhúng SQL vào services
- release/deployment tasks không được bypass repository layer khi cần đọc state hệ thống

### Services layer
- `a2a_public_service`, `public_event_stream`, `orchestration_engine`, `runtime_pool_service` và `policy_engine_v2` là trọng tâm của F32 hardening
- `system_status`, `debug_service`, `operator_dashboard` và `process_manager` là trọng tâm của F33 telemetry
- release readiness nên dựa trên scripts + docs + startup/migration services hiện có thay vì viết flow riêng ngoài hệ thống
- deployment readiness nên tái dùng `config`, `health`, `main` và scripts hiện tại trước khi thêm packaging mới

### CodexBridge layer
- tiếp tục là execution engine duy nhất
- hardening phải làm rõ timeout, cleanup, retry boundary và error propagation quanh bridge
- telemetry phải phản ánh bridge health, failure rate và runtime interaction đủ rõ cho operator

---

## 6. Đề xuất thứ tự triển khai theo sprint nhỏ

### Sprint 15
- F32

### Sprint 16
- F33

### Sprint 17
- F34

### Sprint 18
- F35

---

## 7. Definition of Done cho V4 foundation

V4 foundation được xem là hoàn thành khi:

1. Các flow public/orchestration/runtime quan trọng fail có kiểm soát hơn
2. Có telemetry và correlation đủ để truy vết bottleneck/failure theo thời gian
3. Có release checklist, runbook và smoke gate lặp lại được
4. Có ít nhất một deployment profile tối thiểu được mô tả và verify
5. Docs vận hành, release và readiness đồng bộ với trạng thái thực tế của hệ thống

---

## 8. Ghi chú cuối

Nếu phải chọn giữa:

- mở UI hoặc product surface sớm
- hay khóa reliability, telemetry và release discipline trước

hãy ưu tiên theo thứ tự:

1. hardening và reliability
2. telemetry và observability
3. release readiness
4. deployment readiness

Khi hoàn tất F35, dự án sẽ có một nền V4 đủ cứng để bước sang operator UI mỏng, product UI bước đầu hoặc triển khai rộng hơn mà không phải quay lại sửa các lớp vận hành cốt lõi.
