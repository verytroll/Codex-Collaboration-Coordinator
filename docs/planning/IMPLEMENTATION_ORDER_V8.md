# IMPLEMENTATION_ORDER_V8.md

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/PLAN_V8.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V8.

Khác với `docs/planning/archive/IMPLEMENTATION_ORDER_V7.md`:
- `docs/planning/archive/IMPLEMENTATION_ORDER_V7.md` chốt **PR49-PR54** cho release/support baseline, deployment ergonomics, operator workflow, integration credentials, outbound automation và contract governance
- `docs/planning/IMPLEMENTATION_ORDER_V8.md` chốt **PR56-PR61** cho data lifecycle, durable observability, external guardrails, trust tightening, operator maintenance và V8 release closure

Mục tiêu của tài liệu:
- cho biết sau V7 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review, verify, rollback và handoff dễ hơn
- tách rõ lifecycle, observability, guardrails, trust model, maintenance và release closure
- tránh gộp “long-running baseline work” vào một PR lớn khó kiểm soát và khó chứng minh

---

## 2. Nguyên tắc sắp thứ tự PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải làm hệ thống dễ vận hành dài ngày hơn hoặc làm support claims đáng tin hơn.**
3. **Lifecycle và retention phải đi trước observability persistence.**
4. **Guardrails phải đi trước trust tightening.**
5. **Maintenance workflows phải phản ánh đúng lifecycle, auth và failure semantics đã khóa ở các PR trước.**
6. **Release/support baseline chỉ được claim những phần repo thật sự test, smoke và demo được.**
7. **Ưu tiên theo luồng dùng thật:** lifecycle rõ → observability bền → guardrails rõ → trust sạch → maintenance usable → release baseline rõ.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR56 → PR57 → PR58 → PR59 → PR60 → PR61**

Không có PR nào bị cô lập:
- **PR56** khóa lifecycle/retention assumptions để các PR sau không lưu bền hay claim support trên data model mơ hồ
- **PR57** làm bền incident history trên đúng lifecycle đã chốt ở PR56
- **PR58** thêm guardrails và flow-control semantics dựa trên observability đủ rõ từ PR57
- **PR59** siết trust model sau khi PR58 đã làm rõ limit/error semantics cho external paths
- **PR60** mở maintenance workflows trên đúng auth, lifecycle và hygiene states của PR56-PR59
- **PR61** khóa release/support baseline V8 sau khi lifecycle, observability, guardrails và maintenance paths đều đã được kiểm chứng

---

## 4. Danh sách PR theo thứ tự triển khai

## PR56. Data lifecycle và retention discipline

**Phụ thuộc:** PR55  
**Dựa trên tasks:** F54  
**Mục tiêu:** chốt archive, retention, cleanup và export semantics cho các surface vận hành chính

### Bao gồm
- lifecycle policy cho session, activity, artifacts, public events và webhook deliveries
- archive-first / cleanup semantics rõ cho packaged baseline
- retention window hoặc cleanup cadence tối thiểu
- visibility cơ bản cho archived state, retention backlog và items ngoài retention window
- docs DB/deployment/runbook cho backup-before-prune và cleanup assumptions

### Không bao gồm
- analytics history lớn
- metrics persistence lớn
- trust hardening hoặc auth changes rộng

### Điều kiện merge
- có policy rõ cho ít nhất session/activity, public events và webhook deliveries
- có ít nhất một archive hoặc cleanup path chạy end-to-end
- cleanup không phá replay/debug/audit assumptions đã support
- docs lifecycle/retention không mâu thuẫn nhau

### Demo sau PR
- archive hoặc cleanup một surface thật, sau đó xác nhận operator/debug path vẫn giải thích được state và dữ liệu nằm ngoài retention window

---

## PR57. Durable observability và incident history

**Phụ thuộc:** PR56  
**Dựa trên tasks:** F55  
**Mục tiêu:** làm bền incident history và telemetry summary để operator đọc được sự cố sau restart/handoff

### Bao gồm
- persistence hoặc export path cho incident summaries / telemetry signals quan trọng
- correlation tốt hơn giữa request, session, job, runtime, task, credential và delivery
- history/debug surface tối thiểu cho recent incidents
- docs observability/runbook cho retention assumptions và incident reading

### Không bao gồm
- BI dashboard lớn
- observability platform tách rời
- external guardrails mới

### Điều kiện merge
- có ít nhất một history path bền qua restart
- dashboard/debug/status phản ánh anomaly và correlation nhất quán hơn
- docs giải thích đúng retention/history assumptions
- regression tests cho telemetry/operator diagnostics pass

### Demo sau PR
- tạo một incident nhỏ, restart app, rồi dùng dashboard/debug để đọc lại recent anomaly với correlation context còn giữ được

---

## PR58. External surface guardrails và flow control

**Phụ thuộc:** PR57  
**Dựa trên tasks:** F56  
**Mục tiêu:** thêm giới hạn và failure semantics rõ cho replay, SSE và outbound webhook surfaces

### Bao gồm
- replay window, cursor-gap hoặc slow-consumer semantics rõ hơn
- webhook delivery guardrails và failure behavior khi receiver chậm/lỗi lặp
- rate limiting hoặc quota guardrails nhẹ khi phù hợp
- error/status mapping và operator visibility cho rejection/throttle/retention misses
- docs/tests/conformance notes cập nhật theo guardrails đã claim

### Không bao gồm
- API gateway platform riêng
- distributed event bus
- trust model redesign lớn

### Điều kiện merge
- có guardrail rõ cho ít nhất replay/SSE và webhook paths
- client nhận được error semantics giải thích được
- operator thấy được pressure/limit state ở debug/dashboard hoặc audit path
- guardrail tests pass mà không làm vỡ happy path đang support

### Demo sau PR
- mô phỏng client rơi ngoài retention window hoặc receiver webhook lỗi lặp, rồi quan sát response semantics và operator visibility tương ứng

---

## PR59. Trust tightening và legacy path minimization

**Phụ thuộc:** PR58  
**Dựa trên tasks:** F57  
**Mục tiêu:** làm managed credentials trở thành path external rõ ràng hơn và thu hẹp support claim của legacy bootstrap paths

### Bao gồm
- dọn support claims quanh `ACCESS_TOKEN`, actor headers và managed credentials
- migration/handoff notes cho adopter hiện tại
- credential hygiene và failure explanations tốt hơn
- giữ local-dev/trusted-demo path cần thiết nhưng không over-claim cho adopter
- tests/docs cho managed credential preferred path và reduced legacy path

### Không bao gồm
- SSO enterprise
- self-service IAM portal
- identity model mới ngoài phạm vi existing services

### Điều kiện merge
- support matrix/auth docs không over-claim so với behavior thật
- managed credential path pass end-to-end trên supported surfaces chính
- legacy/bootstrap path được thu hẹp hoặc gắn nhãn rõ
- access boundary và credential lifecycle regression tests pass

### Demo sau PR
- gọi một flow external bằng managed credential, sau đó thử legacy/bootstrap path ở mode compatibility và chứng minh docs phản ánh đúng behavior/support status

---

## PR60. Operator maintenance workflows và hygiene automation

**Phụ thuộc:** PR59  
**Dựa trên tasks:** F58  
**Mục tiêu:** nâng operator surface từ triage/recovery sang maintenance định kỳ và hygiene operations

### Bao gồm
- archive/cleanup workflows tối thiểu cho session-related data khi phù hợp
- credential hygiene flows như rotate/revoke/expire/disable
- webhook hygiene flows như inspect/disable/recover
- maintenance summaries cho retention backlog, expired credentials, disabled integrations và stale state
- runbook/troubleshooting bám theo maintenance operations thật

### Không bao gồm
- admin product lớn ngoài operator scope
- analytics product
- policy automation rộng ngoài hygiene workflows chính

### Điều kiện merge
- có ít nhất một maintenance flow end-to-end cho session/credential/webhook path
- action path có confirmation, reason, audit và operator visibility rõ
- UI/dashboard/runbook không mâu thuẫn nhau
- operator surface regression tests pass

### Demo sau PR
- dùng operator surface để thực hiện một flow maintenance có audit trail rõ, ví dụ disable webhook hoặc expire credential rồi xác nhận hygiene summary cập nhật đúng

---

## PR61. V8 release closure và long-running small-team baseline

**Phụ thuộc:** PR60  
**Dựa trên tasks:** F59  
**Mục tiêu:** chốt V8 thành release/support baseline rõ cho long-running small-team deployment

### Bao gồm
- version bump, release metadata, release notes và upgrade notes cho V8
- release gate, package manifest và smoke path đồng bộ với lifecycle/guardrails/trust assumptions mới
- docs/status/readme đồng bộ với support baseline mới
- support assumptions rõ cho long-running small-team deployment và controlled wider adoption

### Không bao gồm
- broad enterprise support commitments
- nhiều supported deployment profiles cạnh tranh nhau
- rebrand hoặc package surface redesign lớn

### Điều kiện merge
- có release notes và upgrade notes rõ cho V8
- có ít nhất một release candidate/baseline đóng gói lại thành công
- release gate chạy lại được theo docs
- support assumptions, docs và package manifest không drift khỏi nhau

### Demo sau PR
- tạo release candidate V8 cục bộ, chạy lại checklist từ package đến smoke/release gate và xác nhận manifest/docs phản ánh đúng long-running small-team baseline

---

## 5. Mốc giá trị sau từng PR

### Mốc AE — sau PR56
Bạn có:
- lifecycle và retention assumptions rõ hơn cho baseline hiện tại
- nền dữ liệu sạch hơn để làm observability bền

### Mốc AF — sau PR57
Bạn có:
- incident history bền hơn qua restart
- operator handoff/debug path rõ hơn theo thời gian

### Mốc AG — sau PR58
Bạn có:
- external surfaces có guardrails và failure semantics giải thích được
- replay/SSE/webhook paths bớt mơ hồ khi gặp pressure hoặc retention gap

### Mốc AH — sau PR59
Bạn có:
- trust model sạch hơn với managed credentials là đường chính
- legacy/bootstrap claims bị thu hẹp đúng mức

### Mốc AI — sau PR60
Bạn có:
- operator maintenance workflows usable hơn cho chạy dài ngày
- hygiene states dễ thấy hơn thay vì chỉ xử lý khi sự cố đã nổ

### Mốc AJ — sau PR61
Bạn có:
- baseline V8 rõ cho long-running small-team deployment
- nền đủ sạch để bước sang adoption rộng hơn có kiểm soát hoặc hạ tầng mạnh hơn ở phase sau

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:
- `pr/56-data-lifecycle-retention`
- `pr/57-durable-observability-history`
- `pr/58-external-guardrails`
- `pr/59-trust-tightening`
- `pr/60-operator-maintenance`
- `pr/61-v8-release-closure`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:
- code chạy được local hoặc trên supported profile liên quan
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- retention/guardrail/trust/support claims không mập mờ
- có ít nhất một cách demo thủ công
- không mở rộng phạm vi PR quá đà

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự **PR56 → PR61**
- không nhảy sang PR58 hoặc PR59 nếu PR56-PR57 chưa khóa xong lifecycle và observability assumptions

Nếu bạn làm theo sprint:
- có thể gộp **PR56 + PR57** thành một sprint “lifecycle + observability foundation”
- có thể gộp **PR58 + PR59** thành một sprint “guardrails + trust tightening”
- có thể gộp **PR60 + PR61** thành một sprint “maintenance + release closure”
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `docs/planning/PLAN_V8.md`:
- `docs/planning/PLAN_V8.md` trả lời câu hỏi: **phase V8 nhằm giải quyết vấn đề gì**
- `docs/planning/IMPLEMENTATION_TASKS_V8.md` trả lời câu hỏi: **cần làm cụ thể những gì để hoàn tất từng F**
- `docs/planning/IMPLEMENTATION_ORDER_V8.md` trả lời câu hỏi: **nên merge theo thứ tự nào**
