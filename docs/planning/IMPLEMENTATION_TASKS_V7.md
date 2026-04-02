# IMPLEMENTATION_TASKS_V7.md

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/PLAN_V7.md` và `docs/planning/IMPLEMENTATION_ORDER_V7.md` thành backlog thực thi chi tiết cho phase V7.

Khác với `docs/planning/archive/IMPLEMENTATION_TASKS_V6.md`:
- `docs/planning/archive/IMPLEMENTATION_TASKS_V6.md` chốt backlog **F41-F46** cho V5 release closure, operator actions, identity/RBAC cơ bản, durable runtime, realtime streaming và interop certification
- `docs/planning/IMPLEMENTATION_TASKS_V7.md` chốt backlog **F47-F52** cho V6 release/support baseline, deployment ergonomics, operator console polish, integration credentials, outbound automation và contract governance

Mỗi task trong tài liệu này được thiết kế để:
- đủ nhỏ để có thể code và review theo một feature slice rõ
- giữ coordinator-first architecture làm trung tâm
- tiếp tục dùng internal model hiện có làm nguồn sự thật
- buộc supportability, smoke path, docs, audit semantics và demo path đi cùng mỗi bề mặt adoption mới
- tăng dần mức “early-adopter product” thay vì nhảy thẳng sang enterprise platform lớn

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
- Không có task V7 nào đứng riêng lẻ
- Task chốt release/support baseline phải đi cùng smoke path, docs và supported profile rõ
- Task làm deployment ergonomics phải bám một topology được support thật, không trải mỏng nhiều profile nửa vời
- Task polish operator console phải bám theo action/recovery surface hiện có, không đẩy orchestration logic lõi sang UI
- Task mở credential lifecycle phải có principal, scope, rotate/revoke/expire semantics và audit tương ứng
- Task mở outbound integration phải kế thừa queue/retry/recovery semantics đã có thay vì tạo kênh best-effort ngoài luồng
- Task mở governance/conformance phải giới hạn claim đúng với test coverage, smoke path và sample flow thực sự chạy được

---

## 3. Sơ đồ phụ thuộc tổng thể

**F47 → F48 → F49 → F50 → F51 → F52**

Trong đó:
- F47: V6 release closure và support baseline
- F48: team deployment ergonomics và upgrade path
- F49: operator console polish và incident workflow
- F50: integration credentials và access lifecycle
- F51: outbound integration automation
- F52: contract governance và early-adopter conformance

---

## 4. Backlog chi tiết

## F47. V6 release closure và support baseline

**Phụ thuộc:** F46  
**Mở khóa:** F48  
**File hoặc module chính:** `docs/planning/STATUS.md`, `README.md`, `docs/operations/DEPLOYMENT.md`, `docs/operations/LOCAL_SETUP.md`, `docs/operations/RUNBOOK.md`, `docs/releases/RELEASE_NOTES_V6.md`, `docs/releases/UPGRADE_NOTES_V6.md`, `scripts/package_release.ps1`, `scripts/release.ps1`, thư mục `dist/release/`

### Việc cần làm
1. Chốt V6 thành một release/support baseline rõ:
   - version bump
   - release tag strategy
   - release candidate naming
   - release manifest hoặc metadata được làm sạch nếu cần
2. Đồng bộ docs giữa code, package và support assumptions:
   - `docs/planning/STATUS.md`
   - `README.md`
   - deployment notes
   - local setup notes
   - runbook / troubleshooting notes
3. Viết release notes cho các phần đã xong ở V6:
   - operator actions và audit trail
   - identity / team RBAC cơ bản
   - durable runtime
   - realtime streaming
   - interop certification
4. Viết upgrade notes hoặc migration notes tối thiểu cho:
   - durable profile
   - actor/auth headers hoặc credential expectations liên quan
   - streaming behavior hoặc compatibility assumptions nếu có thay đổi quan trọng
5. Chuẩn hóa release verification checklist:
   - package bundle được tạo thành công
   - env file / manifest khớp supported profile chính
   - smoke script chạy trên release bundle
   - readiness / operator surface / public contract smoke path đều có kiểm chứng tối thiểu
6. Làm rõ support baseline nội bộ hoặc early-adopter:
   - profile nào được support chính
   - trust assumptions nào đi cùng
   - giới hạn scope claim ở cuối V6

### Kết quả đầu ra
- V6 không chỉ “đã implementation xong” mà trở thành baseline có version, smoke path và support assumptions rõ
- docs, package, release flow và trạng thái hệ thống không còn lệch nhau
- các PR/task V7 sau có mốc ổn định để bàn giao và so sánh regression

### Điều kiện hoàn thành
- có release notes và upgrade notes rõ cho V6
- có ít nhất một release candidate/baseline được đóng gói lại thành công
- smoke/release verification chạy lại được theo docs
- `docs/planning/STATUS.md` và docs chính không còn mô tả mâu thuẫn về phase, profile support hoặc release baseline

---

## F48. Team deployment ergonomics và upgrade path

**Phụ thuộc:** F47  
**Mở khóa:** F49  
**File hoặc module chính:** `app/core/config.py`, `app/main.py`, `app/services/deployment_readiness.py`, `app/services/release_packaging.py`, `app/services/durable_runtime.py`, `Dockerfile`, script deploy/compose mới nếu cần, `tests/integration/test_small_team_deployment.py`, `tests/integration/test_deployment_readiness.py`, `tests/integration/test_durable_runtime.py`, `docs/operations/DEPLOYMENT.md`, `docs/operations/LOCAL_SETUP.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Chốt một supported durable team profile cho V7:
   - topology chính được support
   - vai trò của API process và runtime/worker boundary
   - profile local-dev nào còn giữ lại và profile nào chỉ còn mang tính tiện dụng
2. Chuẩn hóa bootstrap path:
   - env templates
   - config validation
   - secret/config expectations
   - startup checklist cho người mới
3. Chuẩn hóa upgrade / backup / restore / rollback drills:
   - migration sequencing
   - backup trước thay đổi
   - rollback assumptions
   - failure notes cho các bước nhạy cảm
4. Đồng bộ readiness/smoke path với topology support:
   - readiness checks
   - smoke script
   - package/bundle layout nếu cần
5. Nếu phù hợp, dọn script hoặc bundle structure để deploy path bớt phụ thuộc kiến thức ngầm của người viết repo
6. Viết tests và docs cho:
   - startup với supported profile
   - misconfiguration path chính
   - recovery sau upgrade hoặc restart
   - deployment troubleshooting cơ bản

### Kết quả đầu ra
- một nhóm khác có thể dựng và nâng cấp supported profile với mức suy luận tối thiểu
- bootstrap path, readiness path và smoke path khớp nhau hơn
- docs triển khai phản ánh đúng profile repo thực sự support

### Điều kiện hoàn thành
- boot được ít nhất một durable team profile sạch theo docs
- smoke path và readiness path pass trên profile đã claim
- có backup/restore hoặc rollback notes đủ rõ để lặp lại
- tests deployment/recovery liên quan pass ở phạm vi đã support

---

## F49. Operator console polish và incident workflow

**Phụ thuộc:** F48  
**Mở khóa:** F50  
**File hoặc module chính:** `app/api/operator_dashboard.py`, `app/api/operator_ui.py`, `app/api/operator_realtime.py`, `app/services/operator_dashboard.py`, `app/services/operator_shell.py`, `app/services/operator_actions.py`, `app/services/recovery.py`, `app/models/api/operator_dashboard.py`, `app/models/api/operator_ui.py`, `tests/integration/test_operator_dashboard.py`, `tests/integration/test_operator_ui_smoke.py`, `tests/integration/test_operator_actions.py`, test incident workflow mới nếu cần, `docs/operator/OPERATOR_UI.md`, `docs/operations/RUNBOOK.md`, `docs/operations/TROUBLESHOOTING.md`

### Việc cần làm
1. Xác định tập triage workflow tối thiểu cho V7:
   - xem tình trạng session/job/runtime
   - lần activity gần đây
   - thấy actor/audit context
   - biết recovery path nào đang hợp lệ
2. Mở rộng operator views theo hướng day-2 operations:
   - runtime/queue summary rõ hơn
   - error explanations hoặc failure reasons rõ hơn
   - audit / actor / state change context rõ hơn
3. Chuẩn hóa recovery affordances:
   - retry
   - resume
   - cancel
   - replay hoặc refresh path khi phù hợp
4. Làm rõ incident reading path:
   - timeline hoặc activity grouping tối thiểu
   - liên kết giữa state hiện tại và action gần nhất
   - hiển thị reason/note khi operator hoặc integration actor can thiệp
5. Giữ ranh giới rõ giữa UI và backend:
   - UI không tự quyết orchestration logic
   - business rules vẫn nằm ở service/API layer
6. Viết tests cho:
   - triage happy path
   - recovery happy path
   - busy/error states
   - audit/error context rendering path
7. Cập nhật docs và runbook để operator có thể xử lý một incident nhỏ dựa trên control surface thật thay vì đọc code

### Kết quả đầu ra
- operator surface đủ dùng hơn cho triage, recovery và incident handling hằng ngày
- người vận hành ít phải suy luận từ log thô hoặc nhảy qua nhiều route rời rạc
- UI và runbook ăn khớp nhau hơn

### Điều kiện hoàn thành
- có ít nhất một flow triage → xác định lỗi → recovery hoạt động end-to-end
- audit/error/actor context hiển thị đủ để giải thích hành động gần nhất
- recovery affordances không phá guardrails đã có
- regression tests cho operator surface pass

---

## F50. Integration credentials và access lifecycle

**Phụ thuộc:** F49  
**Mở khóa:** F51  
**File hoặc module chính:** `app/core/config.py`, `app/core/middleware.py`, `app/api/dependencies.py`, `app/services/authz_service.py`, `app/services/access_boundary.py`, service hoặc repository credential mới nếu cần, `app/api/a2a_public.py`, `app/api/a2a_events.py`, `app/api/operator_actions.py`, `app/models/api/identity.py`, `tests/integration/test_public_authz.py`, `tests/integration/test_operator_rbac.py`, test integration credentials mới nếu cần, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`, `docs/integrations/a2a/A2A_PUBLIC_API.md`, `docs/integrations/a2a/A2A_QUICKSTART.md`

### Việc cần làm
1. Thiết kế principal model tối thiểu cho integration clients:
   - principal id
   - display label
   - principal type hoặc purpose
   - source / auth mode
2. Chốt credential lifecycle mức tối thiểu:
   - issue
   - rotate
   - revoke
   - expire
   - bootstrap path an toàn tối thiểu
3. Ánh xạ scope hoặc permission cho:
   - public read/write surfaces
   - event access liên quan
   - operator write paths nếu có nhu cầu nội bộ rõ
4. Làm rõ compatibility với trusted/local path hiện có:
   - path nào tiếp tục giữ cho dev
   - path nào không nên dùng cho adopter
   - migration notes tối thiểu nếu cần đổi thói quen cấu hình
5. Làm giàu audit trail cho credential usage/failures:
   - principal id
   - scope hoặc role
   - auth mode
   - revoke/expire failure context
6. Viết tests cho:
   - allowed credential path
   - forbidden scope path
   - revoked/expired credential path
   - rotate path
   - backward-compatible trusted/local path nếu còn support
7. Cập nhật docs giải thích trust assumptions, bootstrap path và giới hạn của credential model V7

### Kết quả đầu ra
- integration client có principal và credential flow đủ thật để vận hành ngoài nhóm lõi
- access model bớt phụ thuộc vào token dùng chung hoặc trusted path mơ hồ
- audit trail và authz semantics ăn khớp hơn ở external paths

### Điều kiện hoàn thành
- có ít nhất một credential flow hoạt động end-to-end trên supported surface
- rotate hoặc revoke path được kiểm chứng và có audit rõ
- scope checks chặn được các thao tác sai quyền chính
- docs access/credential model đủ để adopter cấu hình mà không phải đoán

---

## F51. Outbound integration automation

**Phụ thuộc:** F50  
**Mở khóa:** F52  
**File hoặc module chính:** `app/services/public_event_stream.py`, `app/services/realtime_transport.py`, `app/services/durable_runtime.py`, delivery service hoặc repository mới nếu cần, `app/repositories/public_events.py`, `app/repositories/public_subscriptions.py`, `app/api/a2a_events.py`, `tests/integration/test_public_streaming.py`, test outbound webhook mới nếu cần, `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`, `docs/integrations/a2a/A2A_QUICKSTART.md`, `docs/operations/RUNBOOK.md`, `docs/operations/DEPLOYMENT.md`

### Việc cần làm
1. Chọn outbound integration path tối thiểu cho V7:
   - webhook delivery hoặc
   - outbound event sink rõ ràng
   Không bắt buộc mở nhiều adapter cùng lúc
2. Chuẩn hóa delivery contract:
   - payload envelope
   - event naming
   - ordering hoặc at-least-once assumptions
   - idempotency expectations cho receiver
3. Làm rõ authenticity và security basics:
   - signature hoặc secret-based verification
   - header expectations
   - failure behavior khi verification mismatch
4. Kế thừa durability đã có:
   - queue/retry semantics
   - dedupe expectations
   - failure visibility
   - replay hoặc re-delivery notes nếu có
5. Mở visibility cho operator:
   - delivery status cơ bản
   - retry/failure context
   - audit trail cho outbound path
6. Viết sample receiver, tests và docs cho:
   - happy path
   - receiver error path
   - retry path
   - signature mismatch hoặc auth failure path
7. Cập nhật adoption notes để external integrator có thể nối coordinator vào workflow ngoài mà không phải giữ stream liên tục

### Kết quả đầu ra
- adopter có một đường nhận sự kiện theo kiểu push thực dụng ngoài polling/streaming
- outbound automation bám vào durability semantics hiện có thay vì tạo kênh mơ hồ mới
- delivery failures bớt âm thầm và dễ quan sát hơn

### Điều kiện hoàn thành
- có ít nhất một outbound delivery path hoạt động end-to-end
- failure/retry path có visibility và audit đủ rõ
- docs mô tả đúng signature, retry assumptions và idempotency expectations
- tests delivery/retry pass ở phạm vi đã claim

---

## F52. Contract governance và early-adopter conformance

**Phụ thuộc:** F51  
**Mở khóa:** roadmap sau V7  
**File hoặc module chính:** `app/api/a2a_public.py`, `app/api/a2a_events.py`, `app/services/a2a_public_service.py`, `docs/integrations/a2a/A2A_PUBLIC_API.md`, `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`, `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`, `docs/integrations/a2a/A2A_QUICKSTART.md`, tài liệu governance/support mới nếu cần, `tests/integration/test_a2a_contract.py`, `tests/integration/test_public_contract.py`, tests conformance hoặc fixtures mới nếu cần

### Việc cần làm
1. Chốt phạm vi support/governance thực sự được hỗ trợ ở cuối V7:
   - public task lifecycle nào được support
   - streaming modes nào được support
   - outbound integration modes nào được support
   - auth/credential modes nào được support
   - deployment assumptions nào đi cùng support claims đó
2. Viết hoặc dọn versioning notes cho supported surface:
   - version bump semantics
   - compatibility expectations
   - deprecation policy tối thiểu
   - support window hoặc support baseline notes
3. Tạo conformance path rõ cho adopter:
   - fixtures
   - checklist
   - sample verify flow
   - contract verification notes
4. Đồng bộ docs giữa internal model và external contract:
   - `session/job/artifact` nội bộ
   - public task/event/outbound view
   - error semantics
   - support/deprecation notes
5. Viết tests cho:
   - supported public contract path
   - supported event/outbound path
   - versioning/conformance assumptions chính
   - docs-backed adopter flow nếu có thể tự động hóa
6. Nếu phù hợp, chuẩn bị release candidate notes cho V7 dựa trên đúng tập support claims đã khóa

### Kết quả đầu ra
- repo có thể tuyên bố một support surface hẹp nhưng có governance rõ hơn
- adopter có đường verify rõ bằng docs + tests + fixtures/checklist
- versioning/support/deprecation claims bớt mơ hồ và đáng tin hơn

### Điều kiện hoàn thành
- contract tests hoặc conformance fixtures pass trên surface được support chính thức
- docs và support matrix không over-claim so với test coverage
- adopter có ít nhất một đường verify rõ theo docs mà không phải đọc sâu vào code
- V7 release candidate notes có thể viết dựa trên bằng chứng kiểm chứng thật

---

## 5. Phụ thuộc chéo theo module

### API layer
- F49 chỉ nên mở operator views và affordances dựa trên action/recovery paths đã có, không chuyển orchestration logic sang frontend
- F50 phải gắn credential/scope checks lên action verbs và public surfaces thật, không chỉ route names
- F51 phải dùng external contract bám replay/event semantics hiện có thay vì tạo event model cạnh tranh
- F52 chỉ nên claim những route, events và outbound flows đã có tests hoặc fixtures tương ứng

### Services layer
- `operator_dashboard`, `operator_shell` và `operator_actions` tiếp tục là điểm neo cho F49, nhưng không nên trở thành nơi nhồi business logic mới thiếu ranh giới
- nếu tạo credential service hoặc principal management mới ở F50, cần tách đủ rõ khỏi middleware/route handlers để tái sử dụng
- nếu tạo outbound delivery service ở F51, cần giữ ownership rành mạch giữa public event generation và outbound transport/retry
- `a2a_public_service` ở F52 phải tiếp tục bám internal model hiện có thay vì sinh ra contract model thứ hai cạnh tranh với coordinator core

### Data / persistence layer
- F48 có thể yêu cầu migration hoặc metadata mới cho topology/deployment bundle nếu cần, nhưng không nên làm phình schema chỉ để phục vụ docs
- F50 có thể yêu cầu bảng hoặc cột mới cho principal/credential/audit context
- F51 có thể yêu cầu queue/delivery metadata mới cho webhook hoặc outbound sink state
- mọi migration mới phải có backup/rollback notes tối thiểu đi kèm và không phá supported path hiện có mà không có migration path rõ

### UI / operator surface
- F49 mở rộng operator console nhưng không biến frontend thành product dashboard tổng quát
- F50 nếu thêm actor/principal context vào UI thì chỉ nên phục vụ vận hành và audit, không kéo sang quản trị danh tính lớn
- F51 chỉ cần đủ visibility để operator biết outbound path đang khỏe hay lỗi; chưa phải phase để xây integration management UI hoàn chỉnh

### Docs / operations
- mọi feature V7 phải cập nhật ít nhất một trong các tài liệu: `docs/planning/STATUS.md`, `README.md`, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`, `docs/operator/OPERATOR_UI.md`, public/A2A docs liên quan
- F47 và F52 là hai điểm bắt buộc phải đồng bộ docs mạnh nhất vì đây là nơi repo tạo release/support claims
- nếu một claim mới không có smoke path, integration test, sample flow hoặc adopter checklist tương ứng, claim đó chưa nên xuất hiện trong docs chính

---

## 6. Thứ tự thực thi tối thiểu nếu cần cắt phạm vi

Nếu thời gian hạn chế, giữ thứ tự sau:
1. F47
2. F48
3. F49
4. F50
5. F51
6. F52

Không nên:
- nhảy sang F50 nếu F47-F49 chưa khóa xong baseline support, deploy path và operator workflow
- mở F51 như một bài toán integration độc lập trước khi credential/auth/audit semantics ở F50 đủ rõ
- tuyên bố governance/conformance ở F52 nếu chưa có test surface, sample flow hoặc adopter verify path thật

---

## 7. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự F47 → F52
- cắt task theo từng feature slice nhỏ bên trong mỗi F
- ưu tiên merge PR nhỏ bám `docs/planning/IMPLEMENTATION_ORDER_V7.md`

Nếu bạn làm theo sprint:
- có thể gộp F47 + F48 thành sprint chốt baseline release và deploy path
- có thể gộp F50 + F51 thành sprint tập trung external integration path
- nhưng vẫn nên giữ review theo feature slices nhỏ, nhất là quanh deploy/auth/outbound/governance

Nếu bạn dùng cùng bộ tài liệu V7:
- `docs/planning/PLAN_V7.md` trả lời câu hỏi: V7 nhằm giải quyết vấn đề gì
- `docs/planning/IMPLEMENTATION_ORDER_V7.md` trả lời câu hỏi: nên merge theo thứ tự nào
- `docs/planning/IMPLEMENTATION_TASKS_V7.md` trả lời câu hỏi: cần làm cụ thể những gì để hoàn tất từng F

