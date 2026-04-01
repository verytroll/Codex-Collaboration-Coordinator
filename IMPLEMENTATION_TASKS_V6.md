# Danh sách nhiệm vụ triển khai giai đoạn V6: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `PLAN_V6.md` và `IMPLEMENTATION_ORDER_V6.md` thành backlog thực thi chi tiết cho phase V6.

Khác với `IMPLEMENTATION_TASKS_V5.md`:
- `IMPLEMENTATION_TASKS_V5.md` chốt backlog **F36-F40** cho access boundary, thin operator UI, realtime operator surface, A2A interoperability và small-team deployment
- `IMPLEMENTATION_TASKS_V6.md` chốt backlog **F41-F46** cho V5 release closure, operator actions, identity/RBAC cơ bản, durable runtime, realtime streaming và interop certification

Mỗi task trong tài liệu này được thiết kế để:
- đủ nhỏ để có thể code và review theo một feature slice rõ
- giữ coordinator-first architecture làm trung tâm
- không đẩy orchestration logic lõi ra khỏi backend
- tăng dần mức “team operations / production control plane” thay vì nhảy thẳng sang distributed platform lớn
- buộc docs, tests, audit semantics và demo path đi cùng mỗi bề mặt mới được mở

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
- Không có task V6 nào đứng riêng lẻ
- Task mở write-action phải đi cùng audit trail và precondition checks
- Task mở identity/RBAC phải bám vào action verbs thật đã tồn tại, không thiết kế trong chân không
- Task mở runtime durability phải giữ migration path rõ từ profile `small-team` hiện có
- Task mở streaming mới phải kế thừa replay/debug semantics đã có ở V5
- Task mở compatibility claims phải có contract tests, sample flow và giới hạn phạm vi claim rõ ràng

---

## 3. Sơ đồ phụ thuộc tổng thể

**F41 → F42 → F43 → F44 → F45 → F46**

Trong đó:
- F41: V5 release closure và baseline discipline
- F42: operator actions và audit trail
- F43: identity và team RBAC cơ bản
- F44: durable runtime và persistence boundary
- F45: realtime streaming transport
- F46: interop certification và external adoption baseline

---

## 4. Backlog chi tiết

## F41. V5 release closure và baseline discipline

**Phụ thuộc:** F40  
**Mở khóa:** F42  
**File hoặc module chính:** `STATUS.md`, `README.md`, `docs/DEPLOYMENT.md`, `docs/LOCAL_SETUP.md`, `docs/RUNBOOK.md`, `scripts/package_release.ps1`, `scripts/smoke.ps1`, thư mục `dist/release/`, release notes hoặc changelog mới

### Việc cần làm
1. Chốt V5 thành một release milestone rõ:
   - version bump
   - release tag strategy
   - release candidate naming
   - release manifest hoặc metadata được làm sạch nếu cần
2. Đồng bộ docs giữa code, package và trạng thái:
   - `STATUS.md`
   - `README.md`
   - deployment notes
   - local setup notes
   - runbook / troubleshooting notes
3. Viết release notes cho các phần đã xong ở V5:
   - access boundary
   - thin operator UI shell
   - realtime operator surface
   - A2A interoperability / adoption kit
   - `small-team` deployment profile
4. Viết upgrade notes hoặc migration notes tối thiểu nếu V5 thay đổi default profile, access mode hoặc packaging path
5. Chuẩn hóa release verification checklist:
   - package bundle được tạo thành công
   - env file / manifest khớp profile `small-team`
   - smoke script chạy trên release bundle
   - readiness / health / operator shell / live activity / public A2A flow đều có kiểm chứng tối thiểu
6. Nếu cần, dọn lại tên script, output structure hoặc dist layout để release path dễ hiểu hơn cho người dùng nội bộ

### Kết quả đầu ra
- V5 không chỉ “đã code xong” mà trở thành baseline có version và verification path rõ
- docs, packaging, smoke path và trạng thái hệ thống không còn lệch nhau
- các PR V6 sau có mốc regression rõ để so sánh

### Điều kiện hoàn thành
- có release notes hoặc changelog rõ cho V5
- có ít nhất một release candidate/baseline được đóng gói lại thành công
- smoke/release verification chạy lại được theo docs
- `STATUS.md` và docs chính không còn mô tả mâu thuẫn về phase hiện tại

---

## F42. Operator actions và audit trail

**Phụ thuộc:** F41  
**Mở khóa:** F43  
**File hoặc module chính:** `app/api/`, `app/services/operator_dashboard.py`, `app/services/approval_service.py`, `app/services/job_service.py`, `app/services/session_service.py`, `app/models/api/`, UI operator shell/console, `tests/integration/test_operator_actions.py`, `tests/integration/test_operator_audit_trail.py`, `docs/OPERATOR_UI.md`, `docs/RUNBOOK.md`

### Việc cần làm
1. Xác định tập operator actions tối thiểu cho V6:
   - approve
   - reject
   - retry
   - resume
   - cancel
   - phase transition có guardrails nếu đã đủ chín
2. Chuẩn hóa write endpoints hoặc command handlers cho các action trên thay vì gắn logic ad hoc vào từng route
3. Làm rõ precondition checks cho mỗi action:
   - action chỉ hợp lệ ở một số trạng thái nhất định
   - action conflict khi state đã đổi
   - action bị chặn khi approval/job/session không còn tồn tại hoặc không còn active
4. Bổ sung capture reason hoặc operator note cho các action cần giải thích:
   - reject
   - cancel
   - manual retry
   - manual phase intervention
5. Mở UI affordances tối thiểu trong operator surface:
   - action buttons hoặc command form
   - confirm step cho action phá vỡ flow
   - pending/busy/error state cho action request
6. Tạo audit trail tối thiểu cho mọi write action quan trọng:
   - actor
   - action type
   - target entity
   - timestamp
   - reason / note nếu có
   - result hoặc failure mode cơ bản
7. Viết tests cho:
   - happy path
   - invalid state path
   - conflict path
   - duplicate action path
   - audit emission path
8. Cập nhật docs cho operator expectations, action semantics và troubleshooting khi action bị từ chối

### Kết quả đầu ra
- operator không chỉ xem state mà còn can thiệp được vào flow thật ở mức tối thiểu
- write actions có guardrails và failure mapping rõ hơn
- mọi thao tác quan trọng đều để lại dấu vết vận hành cơ bản

### Điều kiện hoàn thành
- có ít nhất tập action cốt lõi hoạt động end-to-end từ UI hoặc API
- action sai precondition bị chặn rõ và trả lỗi nhất quán
- audit trail xuất hiện cho mọi operator write action chính
- regression tests cho action paths pass

---

## F43. Identity và team RBAC cơ bản

**Phụ thuộc:** F42  
**Mở khóa:** F44  
**File hoặc module chính:** `app/core/config.py`, `app/api/dependencies.py`, `app/core/middleware.py`, `app/services/authz_service.py` hoặc tương đương, `app/models/`, `app/db/`, `tests/integration/test_operator_rbac.py`, `tests/integration/test_public_authz.py`, `docs/DEPLOYMENT.md`, `docs/OPERATOR_UI.md`, `docs/RUNBOOK.md`

### Việc cần làm
1. Thiết kế actor identity model tối giản nhưng thật:
   - actor id
   - actor type
   - display label hoặc subject
   - source of identity (token/config/dev override)
2. Chốt role model mức cơ bản cho V6:
   - operator
   - reviewer
   - integration client
   - có thể thêm admin nội bộ nếu thật sự cần cho bootstrap
3. Ánh xạ role → action permissions rõ cho:
   - operator write actions
   - public/A2A write surfaces
   - approval/review actions
   - destructive controls như cancel hoặc manual override
4. Mở rộng access boundary từ “có token hay không” sang “ai đang thao tác và có quyền gì” cho các route ghi state chính
5. Làm giàu audit trail bằng identity context:
   - actor id
   - role
   - auth mode
   - source IP hoặc caller context nếu đã có sẵn và không làm phức tạp quá mức
6. Giữ compatibility cho `local` / `trusted` path hiện có để dev flow không bị vỡ quá mạnh
7. Viết tests cho:
   - allowed role path
   - forbidden role path
   - missing identity path
   - backward-compatible local/trusted path
8. Cập nhật docs giải thích trust assumptions, bootstrap identity path và giới hạn của RBAC V6

### Kết quả đầu ra
- write actions quan trọng có actor identity rõ thay vì chỉ dựa trên access token thô
- hệ thống dùng nội bộ theo nhóm bớt mơ hồ ai được làm gì
- audit trail và authorization semantics ăn khớp nhau hơn

### Điều kiện hoàn thành
- action ghi state quan trọng đều có actor context tối thiểu
- role checks chặn được các thao tác sai vai trò chính
- local/trusted profiles vẫn chạy được với đường dev rõ ràng
- docs access model đủ để người khác cấu hình lại mà không phải đoán

---

## F44. Durable runtime và persistence boundary

**Phụ thuộc:** F43  
**Mở khóa:** F45  
**File hoặc module chính:** `app/main.py`, `app/core/config.py`, `app/db/`, `app/services/`, worker/executor modules, `Dockerfile`, docker compose hoặc script deploy nếu có, `tests/integration/test_durable_runtime.py`, `tests/integration/test_recovery_flow.py`, `docs/DEPLOYMENT.md`, `docs/RUNBOOK.md`, migration SQL mới nếu cần

### Việc cần làm
1. Chốt durable profile cho V6:
   - PostgreSQL profile tùy chọn hoặc primary cho team deployment
   - giữ SQLite path hiện có cho local-dev và small-team tối giản nếu vẫn cần
2. Chuẩn hóa config cho persistence/runtime boundary:
   - database selection
   - connection settings
   - worker/executor mode
   - retry / polling / queue related knobs tối thiểu
3. Tách background execution boundary rõ hơn nếu cần:
   - API process
   - worker/executor process hoặc loop riêng
   - tránh nhét mọi background work vào lifecycle ad hoc trong API process
4. Tạo durable delivery pattern tối thiểu cho work hoặc events:
   - outbox / inbox
   - queue table
   - claim/lease/retry semantics
   - idempotency ở mức tối thiểu cho replay/restart
5. Làm rõ recovery semantics:
   - restart API
   - restart worker
   - resume in-flight work
   - duplicate delivery handling
   - orphaned lock/lease cleanup nếu có
6. Cập nhật migration, backup/restore và rollback notes cho profile mới
7. Viết integration tests cho:
   - startup với profile durable
   - migration thành công
   - restart/recovery path
   - at-least-once/dedupe assumptions nếu có
   - backward path cho profile cũ cần còn hỗ trợ
8. Cập nhật topology docs và operational assumptions để người dùng biết khi nào nên dùng profile nào

### Kết quả đầu ra
- hệ thống chịu restart và background execution tốt hơn khi dùng thật trong nhóm
- persistence/runtime boundary không còn phụ thuộc quá nhiều vào một process duy nhất
- profile triển khai bền hơn có docs và test path tương ứng

### Điều kiện hoàn thành
- boot được ít nhất một durable profile sạch và chạy smoke pass
- recovery/restart flow cốt lõi không làm vỡ state chính
- migration path từ profile hiện có được mô tả rõ
- tests recovery/delivery pass ở phạm vi đã claim

---

## F45. Realtime streaming transport

**Phụ thuộc:** F44  
**Mở khóa:** F46  
**File hoặc module chính:** `app/api/`, `app/services/public_event_stream.py`, `app/services/operator_dashboard.py`, `app/models/api/`, UI live modules, `tests/integration/test_operator_streaming.py`, `tests/integration/test_public_streaming.py`, `docs/OPERATOR_UI.md`, `docs/A2A_PUBLIC_EVENTS.md`, `docs/OBSERVABILITY.md`

### Việc cần làm
1. Chọn transport realtime tối thiểu cho V6:
   - SSE hoặc
   - WebSocket
   Không bắt buộc làm cả hai trong cùng phase
2. Chuẩn hóa stream contract mới nhưng vẫn bám replay semantics đã có:
   - stream envelope
   - event ordering assumptions
   - cursor / sequence / replay window mapping
   - event type naming rõ cho operator và public clients
3. Làm rõ reconnect behavior:
   - resume từ cursor
   - xử lý gap ngoài retention window
   - fallback sang replay/polling path nếu transport realtime không khả dụng
4. Giải quyết các concerns tối thiểu của streaming:
   - duplicate delivery awareness
   - keepalive / heartbeat
   - bounded retention/window semantics
   - basic backpressure / slow consumer expectations
5. Nối transport mới vào operator UI hoặc public client examples ở mức đủ để chứng minh value thật, không chỉ có route rời rạc
6. Viết tests cho:
   - subscribe / connect path
   - reconnect path
   - cursor continuity
   - duplicate/resume edge cases
   - replay fallback path nếu có
7. Cập nhật docs cho streaming semantics, retention assumptions và client expectations

### Kết quả đầu ra
- operator và client có realtime transport rõ nghĩa hơn polling đơn thuần
- streaming mới không phá replay/debug path vốn hữu ích ở V5
- client biết cách reconnect hoặc fallback mà không đoán contract

### Điều kiện hoàn thành
- có ít nhất một transport realtime hoạt động end-to-end
- reconnect/cursor resume nhất quán ở flow chính đã claim
- replay path cũ vẫn tồn tại cho debug hoặc fallback
- tests streaming pass

---

## F46. Interop certification và external adoption baseline

**Phụ thuộc:** F45  
**Mở khóa:** roadmap sau V6  
**File hoặc module chính:** `app/api/`, `app/services/a2a_public_service.py`, `docs/A2A_MAPPING.md`, `docs/A2A_PUBLIC_API.md`, `docs/A2A_PUBLIC_EVENTS.md`, `docs/A2A_QUICKSTART.md`, `docs/DEPLOYMENT.md`, `tests/integration/test_a2a_contract.py`, `tests/integration/test_public_contract.py`, sample client scripts / fixtures / examples

### Việc cần làm
1. Chốt phạm vi compatibility claim thực sự được hỗ trợ ở cuối V6:
   - public task lifecycle nào được support
   - event semantics nào được support
   - auth modes nào được support
   - streaming modes nào được support
   - deployment assumptions nào đi cùng claim đó
2. Viết contract tests cho supported surface:
   - task creation / projection
   - task refresh / status read
   - artifact exposure
   - event replay
   - subscription/streaming path đã claim
3. Tạo compatibility matrix ngắn nhưng chính xác:
   - supported
   - experimental
   - out of scope
4. Đồng bộ docs giữa internal model và external contract:
   - `session/job/artifact` nội bộ
   - public task/event view
   - error semantics
   - versioning notes
5. Tạo hoặc dọn sample clients / fixtures / curl scripts để external integrator có thể verify theo docs mà không đọc quá sâu vào code
6. Viết adoption notes cho môi trường thực tế hơn:
   - reverse proxy
   - auth header/token expectations
   - stream transport expectations
   - retention/replay assumptions
   - troubleshooting khi interop mismatch xảy ra
7. Nếu phù hợp, chuẩn bị release candidate notes cho V6 dựa trên đúng tập claim đã test

### Kết quả đầu ra
- repo có thể tuyên bố một compatibility surface hẹp nhưng đáng tin
- external integrator có đường verify rõ bằng docs + tests + sample flow
- public/A2A docs bớt experimental theo nghĩa “đã được chứng minh ở phạm vi cụ thể”

### Điều kiện hoàn thành
- contract tests pass trên surface được support chính thức
- compatibility matrix không over-claim so với test coverage
- sample client hoặc sample scripts chạy được theo docs
- V6 release candidate notes có thể viết dựa trên bằng chứng kiểm chứng thật

---

## 5. Phụ thuộc chéo theo module

### API layer
- operator write-actions của F42 phải đi qua API/service layer rõ, không nhét logic điều phối vào UI
- RBAC ở F43 phải gắn lên action verbs thật, không chỉ route names
- streaming ở F45 phải tương thích với replay window/cursor semantics sẵn có
- public contract ở F46 chỉ nên claim những route/streams đã có tests tương ứng

### Services layer
- `operator_dashboard` tiếp tục là điểm neo cho F42 và F45, nhưng không nên trở thành nơi giữ business logic ghi state lộn xộn
- nếu tạo service authz/audit mới ở F43, cần tách khỏi route handlers đủ rõ để tái sử dụng
- nếu tạo worker/outbox/inbox ở F44, cần giữ ownership rành mạch giữa orchestration service và delivery/runtime service
- `a2a_public_service` ở F46 phải bám internal model hiện có thay vì tạo model thứ hai cạnh tranh với coordinator core

### Data / persistence layer
- F43 có thể yêu cầu bảng hoặc cột mới cho actor/audit context
- F44 có thể yêu cầu migration cho queue/outbox/lease/recovery metadata và profile database mới
- F45 không nên phụ thuộc vào in-memory only semantics nếu muốn stream/reconnect đáng tin
- mọi migration mới phải có docs backup/rollback tối thiểu đi kèm

### UI / operator surface
- F42 mở action controls nhưng không biến frontend thành nơi tự quyết orchestration logic
- F43 nếu thêm actor context vào UI thì chỉ nên thêm phần hiển thị/quản trị tối thiểu, không kéo sang quản trị danh tính lớn
- F45 chỉ cần đủ UI wiring để chứng minh streaming value thật; chưa phải phase cho dashboard product hóa lớn

### Docs / operations
- mọi feature V6 phải cập nhật ít nhất một trong các tài liệu: `STATUS.md`, `docs/OPERATOR_UI.md`, `docs/DEPLOYMENT.md`, `docs/RUNBOOK.md`, public/A2A docs liên quan
- F41 và F46 là hai điểm bắt buộc phải đồng bộ docs mạnh nhất vì đây là nơi repo tạo release claims và interop claims
- nếu một claim mới không có smoke path, integration test hoặc sample flow, claim đó chưa nên xuất hiện trong docs chính

---

## 6. Thứ tự thực thi tối thiểu nếu cần cắt phạm vi

Nếu thời gian hạn chế, giữ thứ tự sau:
1. F41
2. F42
3. F43
4. F44
5. F45
6. F46

Không nên:
- nhảy sang F44 nếu F42/F43 chưa làm rõ action + actor boundary
- mở F45 như một bài toán transport độc lập trước khi persistence/recovery semantics ở F44 đủ rõ
- tuyên bố interop/certification ở F46 nếu chưa có test surface thật

---

## 7. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự F41 → F46
- cắt task theo từng feature slice nhỏ bên trong mỗi F
- ưu tiên merge PR nhỏ bám `IMPLEMENTATION_ORDER_V6.md`

Nếu bạn làm theo sprint:
- có thể gộp F41 + phần đầu F42 thành sprint chốt baseline và mở action surface đầu tiên
- có thể gộp phần cuối F45 + F46 thành sprint chốt release candidate nội bộ
- nhưng vẫn nên giữ review theo feature slices nhỏ, nhất là quanh action/auth/durability

Nếu bạn dùng cùng bộ tài liệu V6:
- `PLAN_V6.md` trả lời câu hỏi: V6 nhằm giải quyết vấn đề gì
- `IMPLEMENTATION_ORDER_V6.md` trả lời câu hỏi: nên merge theo thứ tự nào
- `IMPLEMENTATION_TASKS_V6.md` trả lời câu hỏi: cần làm cụ thể những gì để hoàn tất từng F
