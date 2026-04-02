# IMPLEMENTATION_TASKS_V8.md

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/PLAN_V8.md` thành backlog thực thi chi tiết cho phase V8.

Khác với `docs/planning/archive/IMPLEMENTATION_TASKS_V7.md`:
- `docs/planning/archive/IMPLEMENTATION_TASKS_V7.md` chốt backlog **F47-F52** cho release/support baseline, deployment ergonomics, operator workflow, integration credentials, outbound automation và contract governance
- `docs/planning/IMPLEMENTATION_TASKS_V8.md` chốt backlog **F54-F59** cho data lifecycle, durable observability, external guardrails, trust tightening, operator maintenance và V8 release closure

Mỗi task trong tài liệu này được thiết kế để:
- đủ nhỏ để có thể code và review theo một feature slice rõ
- giữ coordinator-first architecture làm trung tâm
- tiếp tục bám internal model hiện có làm nguồn sự thật
- buộc retention, observability, guardrails, trust model, docs và verification path đi cùng nhau
- tăng dần mức “long-running small-team baseline” thay vì nhảy thẳng sang distributed hoặc enterprise platform lớn

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
- Không có task V8 nào đứng riêng lẻ
- Task data lifecycle phải đi trước observability persistence để tránh lưu bền dữ liệu mà chưa có retention/cleanup policy
- Task guardrails phải đi trước trust tightening để operator và client nhìn thấy failure semantics rõ trước khi support path bị siết lại
- Task maintenance workflow phải phản ánh đúng auth model, retention jobs và hygiene states đã khóa ở các task trước
- Task release/support baseline chỉ được claim các phần đã có tests, smoke path, docs và maintenance flow tương ứng
- Nếu một claim mới không có docs, test, smoke path hoặc conformance/checklist tương ứng, claim đó chưa nên xuất hiện trong docs chính

---

## 3. Sơ đồ phụ thuộc tổng thể

**F54 → F55 → F56 → F57 → F58 → F59**

Trong đó:
- F54: data lifecycle và retention discipline
- F55: durable observability và incident history
- F56: external surface guardrails và flow control
- F57: trust tightening và legacy path minimization
- F58: operator maintenance workflows và hygiene automation
- F59: V8 release closure và long-running small-team baseline

---

## 4. Backlog chi tiết

## F54. Data lifecycle và retention discipline

**Phụ thuộc:** F53  
**Mở khóa:** F55  
**File hoặc module chính:** `app/api/sessions.py`, `app/services/session_events.py`, `app/services/transcript_export.py`, `app/services/public_event_stream.py`, `app/services/outbound_webhooks.py`, repository lifecycle/retention mới nếu cần, `tests/integration/test_session_agent_api.py`, test retention/cleanup mới nếu cần, `docs/operations/RUNBOOK.md`, `docs/operations/DEPLOYMENT.md`, `docs/reference/DB_SCHEMA.md`

### Việc cần làm
1. Chốt lifecycle policy cho các surface chính:
   - session và session-adjacent data
   - session activity và transcript exports
   - artifacts
   - public events / subscriptions
   - outbound webhook deliveries
2. Chuẩn hóa archive-first và cleanup semantics:
   - path nào archive
   - path nào expire hoặc prune
   - path nào phải export trước khi cleanup
   - path nào tuyệt đối không xóa cứng trong baseline V8
3. Thêm retention/cleanup execution path tối thiểu:
   - cleanup cadence hoặc manual operator path
   - config/env defaults cho packaged baseline
   - visibility cho backlog cleanup và items ngoài retention window
4. Làm rõ audit và recovery assumptions:
   - cleanup không phá transcript/audit expectations
   - backup-before-prune notes
   - rollback assumptions khi retention bị cấu hình sai
5. Viết tests và docs cho:
   - archive happy path
   - retention expiry/prune path
   - item ngoài retention window
   - cleanup không làm hỏng supported replay/debug surfaces

### Kết quả đầu ra
- hệ thống có data lifecycle rõ hơn cho vận hành dài ngày
- operator biết dữ liệu nào được giữ, archive hay cleanup và tại sao
- packaged baseline tránh phình dữ liệu âm thầm trên các surface đang support

### Điều kiện hoàn thành
- có policy rõ cho ít nhất session/activity, public events và webhook deliveries
- có ít nhất một cleanup/archive path chạy được end-to-end
- docs DB/deployment/runbook không mâu thuẫn nhau về retention assumptions
- tests cho lifecycle/cleanup chính pass ở phạm vi đã claim

---

## F55. Durable observability và incident history

**Phụ thuộc:** F54  
**Mở khóa:** F56  
**File hoặc module chính:** `app/core/telemetry.py`, `app/services/debug_service.py`, `app/services/system_status.py`, `app/services/operator_dashboard.py`, `app/services/operator_realtime.py`, persistence/repository mới cho incident history nếu cần, `app/api/system.py`, `app/api/operator_dashboard.py`, `tests/integration/test_system_telemetry.py`, `tests/integration/test_operator_dashboard.py`, `docs/operations/OBSERVABILITY.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Xác định tập signal cần bền qua restart:
   - incident summaries
   - failure hotspots
   - auth/delivery/runtime anomalies chính
   - recent activity slices phục vụ handoff
2. Bổ sung durable history path tối thiểu:
   - persistence hoặc export path cho telemetry/incident summary quan trọng
   - retention window khớp F54
   - không biến thành metrics platform lớn
3. Chuẩn hóa correlation và đọc incident:
   - request/session/job/runtime/task/credential/delivery correlation rõ hơn
   - debug/status/dashboard bám cùng một semantics
   - handoff sau restart vẫn đọc được recent incidents cơ bản
4. Mở visibility cho operator:
   - history/debug surface tối thiểu
   - explanation rõ hơn cho anomaly gần nhất
   - timeline hoặc summary đủ để giảm phụ thuộc log thô
5. Viết tests và docs cho:
   - incident history survive restart path tối thiểu
   - telemetry/history retention assumptions
   - correlation fields và debug semantics chính

### Kết quả đầu ra
- operator có observability bền hơn cho troubleshooting dài ngày
- recent incidents không mất hoàn toàn sau restart
- history/debug surface đủ rõ để handoff ca trực hoặc điều tra chậm

### Điều kiện hoàn thành
- có ít nhất một incident/history path bền qua restart
- dashboard/debug/status thể hiện correlation và anomaly context nhất quán hơn
- docs observability/runbook giải thích đúng history assumptions
- regression tests cho telemetry/operator diagnostics pass

---

## F56. External surface guardrails và flow control

**Phụ thuộc:** F55  
**Mở khóa:** F57  
**File hoặc module chính:** `app/core/middleware.py`, `app/services/public_event_stream.py`, `app/services/realtime_transport.py`, `app/services/outbound_webhooks.py`, `app/services/access_boundary.py`, `app/api/a2a_events.py`, `app/api/outbound_webhooks.py`, test guardrails/streaming mới nếu cần, `tests/integration/test_public_streaming.py`, `tests/integration/test_outbound_webhooks.py`, `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`, `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`, `docs/operations/RUNBOOK.md`

### Việc cần làm
1. Chốt guardrails tối thiểu cho supported external paths:
   - replay window
   - SSE slow-consumer hoặc cursor-gap semantics
   - webhook delivery limits hoặc failure behavior khi receiver chậm/lỗi lặp
   - rate limiting hoặc quota guardrails nhẹ khi cần
2. Chuẩn hóa error/status mapping:
   - response khi client vượt limit
   - response khi cursor rơi ngoài retention window
   - response khi delivery path bị disable, exhausted hoặc throttled
3. Giữ semantics nhất quán giữa docs, contract tests và runtime:
   - supported surface nào bị guardrail
   - semantics nào chỉ là compatibility path
   - signal nào phải xuất hiện trong debug/operator visibility
4. Thêm visibility và audit context:
   - lý do bị throttle hoặc reject
   - counters/summaries tối thiểu cho operator
   - troubleshooting path rõ trong runbook
5. Viết tests và docs cho:
   - replay/SSE vượt retention window
   - slow consumer / resume gap
   - webhook failure hoặc delivery limit path
   - guardrail path không phá supported happy path hiện có

### Kết quả đầu ra
- external surfaces có giới hạn rõ hơn cho dùng thật dài ngày
- client nhận được failure semantics giải thích được thay vì hành vi mơ hồ
- operator thấy được pressure/limit state thay vì chỉ thấy timeout hoặc retry âm thầm

### Điều kiện hoàn thành
- có guardrail rõ cho ít nhất replay/SSE và webhook paths
- docs compatibility/governance phản ánh đúng guardrails đã claim
- tests guardrail/failure path pass và không làm vỡ happy path đã support
- runbook chỉ ra được cách đọc và phục hồi từ các guardrail chính

---

## F57. Trust tightening và legacy path minimization

**Phụ thuộc:** F56  
**Mở khóa:** F58  
**File hoặc module chính:** `app/core/config.py`, `app/core/middleware.py`, `app/api/dependencies.py`, `app/services/access_boundary.py`, `app/services/authz_service.py`, `app/services/integration_credentials.py`, `app/api/integration_credentials.py`, `tests/integration/test_access_boundary.py`, `tests/integration/test_public_authz.py`, `tests/integration/test_integration_credentials.py`, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`, `docs/integrations/a2a/A2A_PUBLIC_API.md`, `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`

### Việc cần làm
1. Chốt trust model long-running baseline:
   - managed credentials là external path chính
   - shared bootstrap token còn giữ cho use case nào
   - actor header path nào là supported, path nào là compatibility/dev-only
2. Dọn support claims và behavior:
   - giảm phạm vi docs của legacy bootstrap path
   - ghi rõ migration/handoff notes cho adopter hiện tại
   - tránh để support matrix rộng hơn runtime behavior thật
3. Làm giàu hygiene và failure explanations:
   - rotate/revoke/expire/disable semantics rõ hơn
   - audit context cho legacy path usage
   - operator visibility cho credential health và auth failures chính
4. Giữ backward path hợp lý cho local/dev:
   - không làm local-dev, trusted-demo hoặc smoke path gãy vô ích
   - vẫn giữ compatibility path tối thiểu cho bootstrap khi cần
5. Viết tests và docs cho:
   - managed credential preferred path
   - reduced legacy/compatibility claim path
   - revoked/expired/disabled behavior
   - migration notes cho external clients

### Kết quả đầu ra
- trust model sạch hơn cho deployment chạy lâu ngày
- managed credentials trở thành path mặc định rõ ràng cho integrator
- legacy bootstrap paths không còn bị hiểu nhầm là supported external model chính

### Điều kiện hoàn thành
- support matrix và docs auth không over-claim so với behavior thật
- managed credential path pass end-to-end trên supported surfaces chính
- legacy/bootstrap behavior được thu hẹp hoặc gắn nhãn rõ trong docs/tests
- regression tests cho access boundary và credential lifecycle pass

---

## F58. Operator maintenance workflows và hygiene automation

**Phụ thuộc:** F57  
**Mở khóa:** F59  
**File hoặc module chính:** `app/api/operator_dashboard.py`, `app/api/operator_ui.py`, `app/api/integration_credentials.py`, `app/api/outbound_webhooks.py`, `app/api/sessions.py`, `app/services/operator_dashboard.py`, `app/services/operator_shell.py`, `app/services/integration_credentials.py`, `app/services/outbound_webhooks.py`, maintenance service mới nếu cần, `tests/integration/test_operator_dashboard.py`, `tests/integration/test_operator_ui_smoke.py`, test maintenance workflow mới nếu cần, `docs/operator/OPERATOR_UI.md`, `docs/operations/RUNBOOK.md`, `docs/operations/TROUBLESHOOTING.md`

### Việc cần làm
1. Xác định tập maintenance workflow tối thiểu cho V8:
   - archive hoặc cleanup session-related data
   - credential hygiene: rotate/revoke/expire/disable
   - webhook hygiene: disable/inspect/recover
   - stale runtime hoặc periodic recovery drill khi phù hợp
2. Mở operator visibility theo hướng maintenance:
   - retention backlog
   - expired/disabled credential summaries
   - outbound integration hygiene summaries
   - stale state warnings cần operator can thiệp
3. Chuẩn hóa action path và guardrails:
   - confirmation/reason/audit semantics
   - không đẩy business logic xuống UI
   - recovery/rollback notes rõ cho action nhạy cảm
4. Đồng bộ UI, dashboard và runbook:
   - operator shell hoặc dashboard cho maintenance affordances tối thiểu
   - troubleshooting notes bám đúng action path thật
   - không biến thành admin product lớn ngoài control plane
5. Viết tests và docs cho:
   - maintenance happy path
   - guardrail path
   - failure/retry/recovery path
   - audit rendering và operator explanation path

### Kết quả đầu ra
- operator có bề mặt làm việc cho maintenance định kỳ, không chỉ đợi sự cố xảy ra
- hygiene states quan trọng dễ thấy hơn trong dashboard/debug/UI
- runbook bám sát workflows vận hành thật hơn

### Điều kiện hoàn thành
- có ít nhất một flow maintenance end-to-end cho session/credential/webhook path
- action path có audit, reason và operator visibility rõ
- UI/dashboard/runbook không mâu thuẫn nhau về maintenance semantics
- regression tests cho operator surface và maintenance actions pass

---

## F59. V8 release closure và long-running small-team baseline

**Phụ thuộc:** F58  
**Mở khóa:** roadmap sau V8  
**File hoặc module chính:** `docs/planning/STATUS.md`, `README.md`, `docs/operations/DEPLOYMENT.md`, `docs/operations/LOCAL_SETUP.md`, `docs/operations/RUNBOOK.md`, `docs/releases/RELEASE_NOTES_V8.md`, `docs/releases/UPGRADE_NOTES_V8.md`, `scripts/release.ps1`, `scripts/package_release.ps1`, `app/services/release_packaging.py`, `tests/unit/test_release_packaging.py`

### Việc cần làm
1. Chốt V8 thành release/support baseline rõ:
   - version bump
   - release tag strategy
   - release candidate naming
   - package manifest phản ánh đúng long-running small-team assumptions
2. Đồng bộ docs giữa code, package và support assumptions:
   - status, readme, deployment, local setup, runbook
   - release notes / upgrade notes
   - compatibility/governance docs nếu claim thay đổi
3. Chuẩn hóa release gate cho baseline mới:
   - smoke/release verification
   - docs registry / package manifest checks
   - conformance path nếu external support claim thay đổi
   - maintenance/lifecycle assumptions được verify tối thiểu
4. Làm rõ support baseline V8:
   - small-team long-running assumptions nào được support chính
   - trust/retention/guardrail expectations nào đi kèm
   - adoption claims nào vẫn còn hẹp hoặc compatibility-only
5. Viết tests và docs cho:
   - release packaging/manifest
   - versioned release metadata
   - upgrade notes cho adopter hiện tại
   - synchronized release checklist

### Kết quả đầu ra
- V8 trở thành baseline release rõ cho long-running small-team deployment
- docs, package, status và release gate không drift khỏi nhau
- phase sau V8 có mốc ổn định để mở rộng adoption hoặc hạ tầng tiếp theo

### Điều kiện hoàn thành
- có release notes và upgrade notes rõ cho V8
- có ít nhất một release candidate/baseline được đóng gói lại thành công
- release gate chạy lại được theo docs và phản ánh đúng assumptions mới
- `docs/planning/STATUS.md` và docs chính không còn mô tả mâu thuẫn về phase, profile support hoặc release baseline

---

## 5. Phụ thuộc chéo theo module

### API layer
- F54 phải mở archive/cleanup path theo model dữ liệu hiện có, không dùng route handlers để quyết định retention policy rải rác
- F55 nên mở rộng `system/status`, `system/debug` và `operator/dashboard` theo semantics nhất quán thay vì tạo nhiều debug route riêng lẻ
- F56 phải giữ replay/SSE/webhook semantics bám contract public hiện có, chỉ thêm guardrails và error mapping rõ hơn
- F57 chỉ nên thu hẹp support claims sau khi behavior thật và migration notes đã rõ
- F58 nên giữ UI/operator actions mỏng, mọi maintenance rule phải nằm ở service/API layer
- F59 chỉ nên claim release/support surface nào đã có smoke/tests/docs tương ứng

### Services layer
- F54 nên có ownership rõ giữa lifecycle policy, cleanup execution và export/audit preservation
- F55 nên tái sử dụng telemetry/debug/dashboard model thay vì tạo observability model song song cạnh tranh
- F56 cần tập trung guardrail enforcement ở boundary/service rõ ràng, không rải quota/limit logic theo từng route nhỏ
- F57 nên bám `access_boundary`, `authz_service` và `integration_credentials` như điểm neo chính cho trust model
- F58 nếu thêm maintenance service mới thì phải tách rõ khỏi shell/dashboard rendering để dễ test và reuse

### Data / persistence layer
- F54 có thể cần migration hoặc metadata mới cho archive/retention/cleanup state
- F55 có thể cần persistence tối thiểu cho telemetry hoặc incident summaries
- F56 có thể cần state/counter/window metadata cho guardrails nếu runtime behavior đòi hỏi
- mọi migration mới phải có backup/rollback notes tối thiểu và không làm vỡ packaged small-team baseline

### UI / operator surface
- F55 và F58 nên ưu tiên explainability cho operator, không biến UI thành analytics product lớn
- F56 chỉ cần đủ visibility để operator hiểu limit/pressure/rejection state, chưa phải phase để xây API gateway console
- F58 mở maintenance affordances nhưng không nên drift thành admin product rộng ngoài control-plane needs

### Docs / operations
- mọi feature V8 phải cập nhật ít nhất một trong các tài liệu: `docs/planning/STATUS.md`, `README.md`, `docs/operations/DEPLOYMENT.md`, `docs/operations/RUNBOOK.md`, `docs/operations/OBSERVABILITY.md`, docs public/A2A liên quan
- F54 và F59 là hai điểm phải đồng bộ docs mạnh nhất vì đây là nơi repo khóa lifecycle assumptions và release/support claims
- nếu một claim mới không có smoke path, integration test, contract test, sample flow hoặc operator verify path tương ứng, claim đó chưa nên xuất hiện trong docs chính

---

## 6. Thứ tự thực thi tối thiểu nếu cần cắt phạm vi

Nếu thời gian hạn chế, giữ thứ tự sau:
1. F54
2. F55
3. F56
4. F57
5. F58
6. F59

Không nên:
- nhảy sang F56 nếu F54-F55 chưa khóa xong lifecycle và observability assumptions của baseline hiện tại
- siết trust model ở F57 trước khi guardrail/error semantics ở F56 đủ rõ cho operator và adopter
- mở F58 như bài toán UI độc lập trước khi auth/lifecycle/guardrail semantics ở F54-F57 đủ ổn
- tuyên bố release/support baseline ở F59 nếu chưa có maintenance path, smoke path hoặc docs tương ứng cho các claim mới

---

## 7. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự F54 → F59
- cắt task theo từng feature slice nhỏ bên trong mỗi F
- ưu tiên merge PR nhỏ và tránh trộn lifecycle, observability, guardrails, auth và release closure trong cùng một PR

Nếu bạn làm theo sprint:
- có thể gộp F54 + F55 thành sprint “long-running lifecycle + observability foundation”
- có thể gộp F56 + F57 thành sprint “external guardrails + trust tightening”
- có thể gộp F58 + F59 thành sprint “maintenance + release closure”
- nhưng vẫn nên giữ review theo feature slices nhỏ, nhất là quanh retention/auth/guardrail changes

Nếu bạn dùng cùng bộ tài liệu V8:
- `docs/planning/PLAN_V8.md` trả lời câu hỏi: V8 nhằm giải quyết vấn đề gì
- `docs/planning/IMPLEMENTATION_TASKS_V8.md` trả lời câu hỏi: cần làm cụ thể những gì để hoàn tất từng F
- `docs/planning/IMPLEMENTATION_ORDER_V8.md` nên trả lời câu hỏi: nên merge theo thứ tự nào
