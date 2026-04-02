# IMPLEMENTATION_TASKS_V5.md

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/archive/PLAN_V5.md` thành backlog thực thi chi tiết cho phase V5.

Khác với `docs/planning/archive/IMPLEMENTATION_TASKS_V4.md`:
- `docs/planning/archive/IMPLEMENTATION_TASKS_V4.md` chốt backlog **F32-F35** cho V4 hardening, telemetry, release readiness và deployment readiness
- `docs/planning/archive/IMPLEMENTATION_TASKS_V5.md` chốt backlog **F36-F40** cho V5 access boundary, thin operator UI, realtime operator surface, A2A interoperability và small-team deployment

Mỗi task trong tài liệu này được thiết kế để:
- đủ nhỏ để có thể code và review theo một feature slice rõ
- có phụ thuộc tuần tự rõ ràng giữa access boundary, UI shell, live surface, interoperability và deployment profile
- giữ coordinator-first architecture làm trung tâm
- ưu tiên mở lớp sử dụng thật trên nền V4 đã ổn định, thay vì trộn lại với một vòng hardening chung chung nữa

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
- Không có task V5 nào đứng riêng lẻ
- Mỗi task V5 nhận đầu vào từ task trước hoặc từ nền V4 đã có
- Nếu task mở thêm access surface, UI surface hoặc interoperability surface, docs và tests liên quan phải đi cùng
- Nếu task thêm profile triển khai mới, smoke/release path tương ứng phải được cập nhật cùng lúc

---

## 3. Sơ đồ phụ thuộc tổng thể

**F36 → F37 → F38 → F39 → F40**

Trong đó:
- F36: access boundary và external safety baseline
- F37: thin operator UI shell
- F38: realtime operator surface
- F39: A2A interoperability và adoption kit
- F40: small-team deployment profile và release packaging

---

## 4. Backlog chi tiết

## F36. Access boundary và external safety baseline

**Phụ thuộc:** F35  
**Mở khóa:** F37  
**File hoặc module chính:** `app/core/config.py`, `app/api/dependencies.py`, `app/api/`, `app/core/middleware.py`, `app/services/`, `tests/integration/test_access_boundary.py`, `docs/operations/LOCAL_SETUP.md`, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Chuẩn hóa chế độ truy cập tối thiểu cho operator/public surface:
   - local-dev trusted mode
   - protected mode cho operator/public routes
   - config profile rõ để bật/tắt access boundary
2. Thêm API key hoặc service token flow tối thiểu cho các route cần mở ra ngoài local loop
3. Rà soát route grouping để phân biệt rõ hơn:
   - route nội bộ
   - route operator
   - route public/A2A
4. Gắn audit/log context tối thiểu cho:
   - successful access decisions
   - failed auth attempts
   - denied operator/public actions
5. Viết integration tests cho:
   - unauthorized
   - forbidden
   - allowed
   - backward-compatible local path
6. Cập nhật docs cho local-dev, trusted-demo và protected mode

### Kết quả đầu ra
- operator/public surface có lớp truy cập tối thiểu nhưng rõ
- môi trường non-local có baseline an toàn hơn mặc định local hiện tại
- người vận hành biết bật/tắt access boundary theo profile mà không phải tự suy đoán

### Điều kiện hoàn thành
- ít nhất một cơ chế bảo vệ tối thiểu có thể bật bằng config
- local-first path cũ vẫn hoạt động gọn cho phát triển hằng ngày
- access failures trả về nhất quán ở mức cơ bản
- tests access baseline pass

---

## F37. Thin operator UI shell

**Phụ thuộc:** F36  
**Mở khóa:** F38  
**File hoặc module chính:** thư mục UI mới (ví dụ `ui/` hoặc `webui/`), `app/api/`, `app/models/api/`, `app/services/operator_dashboard.py`, `tests/integration/test_operator_ui_shell.py`, `docs/operator/OPERATOR_UI.md`

### Việc cần làm
1. Tạo UI shell tối thiểu cho các thực thể vận hành chính:
   - sessions
   - participants
   - messages / transcript
   - jobs / phases
   - approvals
   - artifacts
2. Thêm filters và summary cards cơ bản theo:
   - session
   - status
   - runtime
   - template
   - approval state
3. Tạo UI client/service layer bọc API hiện có thay vì đưa orchestration logic vào frontend
4. Chuẩn hóa loading, empty state, error state và refresh path ở các màn hình chính
5. Nếu cần, bổ sung read model hoặc API response shaping nhỏ để UI đọc ổn định hơn mà không làm bẩn core model
6. Viết docs setup UI local và smoke tests hoặc UI tests cơ bản cho các flow đọc chính

### Kết quả đầu ra
- operator có một giao diện mỏng nhưng đủ dùng để quan sát hệ thống hằng ngày
- trải nghiệm vận hành bớt phụ thuộc vào việc ghép nhiều route thủ công
- UI bám state thật từ backend thay vì tạo orchestration model riêng

### Điều kiện hoàn thành
- có thể mở UI và theo dõi được một session cùng transcript, jobs, approvals và artifacts từ một chỗ
- UI không nắm logic điều phối lõi
- các flow đọc chính có smoke/test path tối thiểu
- docs setup UI đủ để người khác chạy lại

---

## F38. Realtime operator surface

**Phụ thuộc:** F37  
**Mở khóa:** F39  
**File hoặc module chính:** `app/services/public_event_stream.py`, `app/services/operator_dashboard.py`, `app/api/`, `app/models/api/`, module UI live feed/timeline, `tests/integration/test_operator_realtime_surface.py`, `docs/operations/OBSERVABILITY.md`, `docs/operator/OPERATOR_UI.md`

### Việc cần làm
1. Chuẩn hóa live stream contract cho operator UI:
   - message events
   - job lifecycle events
   - phase transitions
   - review / approval events
   - runtime health/activity events
2. Làm rõ reconnect, replay hoặc since/cursor semantics cho UI clients
3. Tạo activity feed hoặc session timeline để gom các event gần đây vào một surface dễ đọc
4. Hiển thị rõ hơn trong UI:
   - pending approvals
   - recent errors
   - stuck jobs
   - phase bottlenecks
   - runtime health bất thường
5. Mở rộng tests cho live/replay behavior, cursor edge cases và reconnect path
6. Viết docs cho event semantics phía operator/UI

### Kết quả đầu ra
- operator nhìn thấy activity sống thay vì chỉ refresh thủ công hoặc đọc diagnostics rời rạc
- state gần đây có thể phục hồi cơ bản sau reconnect
- tín hiệu stuck/pending/error dễ thấy hơn trong bề mặt vận hành

### Điều kiện hoàn thành
- UI nhận được event lifecycle chính theo thời gian thực
- reconnect hoặc reload vẫn quan sát được recent activity ở mức tối thiểu
- live surface trả lời được câu hỏi “điều gì vừa xảy ra” và “đang tắc ở đâu”
- tests live/replay pass

---

## F39. A2A interoperability và adoption kit

**Phụ thuộc:** F38  
**Mở khóa:** F40  
**File hoặc module chính:** `app/api/`, `app/services/a2a_public_service.py`, `docs/integrations/a2a/A2A_MAPPING.md`, `docs/integrations/a2a/A2A_QUICKSTART.md`, `docs/operations/TROUBLESHOOTING.md`, `tests/integration/test_a2a_interoperability.py`, script demo hoặc examples cho external client

### Việc cần làm
1. Hoàn thiện `/.well-known/agent-card.json` và discovery metadata ở mức hữu ích thực tế hơn
2. Chuẩn hóa mapping docs giữa internal model và public/A2A model:
   - task lifecycle
   - event semantics
   - artifact/outcome exposure
   - compatibility notes
3. Viết interoperability smoke flow:
   - external client tạo task
   - theo dõi event/status
   - đọc artifact hoặc outcome
4. Bổ sung compatibility tests cho public/A2A surface quan trọng
5. Tạo adoption kit tối thiểu:
   - curl examples
   - script examples
   - quickstart cho external integrator
   - troubleshooting notes cho public flows
6. Nếu cần, làm rõ versioning notes hoặc compatibility guarantees tối thiểu

### Kết quả đầu ra
- public/A2A surface chuyển từ mức “có route” sang mức “tích hợp được và verify được”
- external integrator có đường vào rõ mà không phải đọc code lõi quá sâu
- discovery metadata không còn chỉ là placeholder báo trước

### Điều kiện hoàn thành
- một external client/agent mẫu có thể đi qua smoke flow end-to-end
- docs public/A2A đủ để người khác tích hợp ở mức cơ bản
- compatibility tests cho surface chính pass
- public claims có demo path tương ứng

---

## F40. Small-team deployment profile và release packaging

**Phụ thuộc:** F39  
**Mở khóa:** roadmap xa hơn  
**File hoặc module chính:** `app/core/config.py`, `app/main.py`, `Dockerfile`, `scripts/run.ps1`, `scripts/dev.ps1`, `scripts/smoke.ps1`, `scripts/release.ps1`, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`, `docs/operations/LOCAL_SETUP.md`, `tests/integration/test_small_team_deployment.py`

### Việc cần làm
1. Chuẩn hóa profile cấu hình rõ cho:
   - local-dev
   - trusted-demo
   - small-team deployment
2. Nếu cần, thêm persistence/dependency option phù hợp hơn cho profile nhóm nhỏ mà không phá local-first path
3. Cập nhật deployment docs cho:
   - reverse proxy
   - secret handling
   - migration strategy
   - backup/restore
   - rollback tối thiểu
4. Mở rộng smoke/release scripts để phản ánh profile mới thay vì chỉ local conservative path
5. Cập nhật README, release docs, upgrade notes và STATUS để mô tả đúng V5 foundation
6. Viết tests hoặc smoke checks cho startup, readiness, restart và smoke flow ở profile mới

### Kết quả đầu ra
- có ít nhất một deployment profile thực dụng cho nhóm nhỏ
- release packaging và smoke path bám đúng profile mới
- local-first vẫn giữ được như mặc định phát triển chính

### Điều kiện hoàn thành
- profile small-team có docs rõ và smoke path tương ứng
- release/smoke scripts phản ánh profile mới
- local-dev path không bị regression đáng kể
- docs vận hành, release và trạng thái hệ thống đồng bộ với cấu hình/code mới

---

## 5. Phụ thuộc chéo theo module

### API layer
- access boundary không được nhét rải rác thành logic auth ad hoc ở từng route
- UI-facing read models nên đi qua API/service layer rõ thay vì frontend tự ghép state không chính tắc
- interoperability surface phải giữ compatibility và semantics rõ hơn so với route thử nghiệm

### Services layer
- `operator_dashboard`, `public_event_stream` và `a2a_public_service` là trọng tâm của F37-F39
- access decisions nên tái dùng dependencies/config/middleware trước khi sinh thêm service flow mới
- UI và interoperability không được kéo core orchestration logic ra ngoài coordinator/service layer

### UI / Interface layer
- UI chỉ hiển thị state và gọi API/service layer
- realtime UI phải bám event/replay contract thay vì polling ad hoc
- operator UI nên ưu tiên observability và control surface, không mở rộng thành product workflow lớn quá sớm

### Config / Deployment layer
- mọi profile môi trường mới phải đi cùng docs và smoke path
- small-team deployment không được làm local-dev path phức tạp quá mức
- secret handling, reverse proxy và migration notes phải được mô tả từ cùng một config contract

### Docs / Examples layer
- docs A2A và docs operator UI phải phản ánh đúng contract hiện có
- adoption kit phải dùng được thật, không chỉ là placeholder marketing
- status/release docs phải cập nhật cùng khi chuyển từ planning sang implementation

---

## 6. Đề xuất thứ tự triển khai theo sprint nhỏ

### Sprint 19
- F36

### Sprint 20
- F37

### Sprint 21
- F38

### Sprint 22
- F39

### Sprint 23
- F40

---

## 7. Definition of Done cho V5 foundation

V5 foundation được xem là hoàn thành khi:
1. operator/public surface có access boundary tối thiểu, cấu hình rõ và không làm hỏng local-first path
2. có thin operator UI đủ dùng cho quan sát và điều phối cơ bản
3. operator theo dõi được session/job/phase/approval/runtime theo thời gian thực
4. public/A2A surface có docs, demo flow và compatibility tests rõ
5. có ít nhất một deployment profile thực dụng cho nhóm nhỏ với smoke/release path tương ứng
6. docs UI, A2A, deployment, release và STATUS đồng bộ với trạng thái thực tế của hệ thống

---

## 8. Ghi chú cuối

Nếu phải chọn giữa:
- thêm nhiều product workflow mới
- hay khóa access boundary, operator UI, realtime visibility và interoperability trước

hãy ưu tiên theo thứ tự:
1. access boundary
2. thin operator UI
3. realtime operator surface
4. A2A interoperability
5. small-team deployment

Khi hoàn tất F40, dự án sẽ có một nền V5 đủ sạch để bước tiếp sang operator UX sâu hơn, external adoption thực tế hơn hoặc mở các roadmap lớn hơn mà không phải quay lại sửa lại các lớp tiếp cận và triển khai cơ bản.

