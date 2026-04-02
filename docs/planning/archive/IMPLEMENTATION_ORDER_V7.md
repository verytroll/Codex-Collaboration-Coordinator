# IMPLEMENTATION_ORDER_V7.md

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `docs/planning/archive/PLAN_V7.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V7.

Khác với `docs/planning/archive/IMPLEMENTATION_ORDER_V6.md`:
- `docs/planning/archive/IMPLEMENTATION_ORDER_V6.md` chốt **PR43-PR48** cho release closure, operator actions, team RBAC, durable runtime, realtime streaming và interop certification
- `docs/planning/archive/IMPLEMENTATION_ORDER_V7.md` chốt **PR49-PR54** cho V6 release/support baseline, deployment ergonomics, operator console polish, integration credentials, outbound automation và contract governance

Mục tiêu của tài liệu:
- cho biết sau V6 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review, verify, rollback và handoff dễ hơn
- tách rõ productization, deployment, day-2 operations, credentials, outbound integrations và contract governance
- tránh gộp “adoption work” vào một PR lớn khó kiểm soát và khó chứng minh

---

## 2. Nguyên tắc sắp thứ tự PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải làm hệ thống dễ bàn giao hơn, dễ vận hành hơn hoặc dễ kiểm chứng claim hơn.**
3. **PR chốt release/support baseline phải đi trước mọi mở rộng adoption surface.**
4. **PR làm deployment ergonomics phải bám vào một supported profile thật, không trải mỏng nhiều topology.**
5. **PR polish operator console phải phản ánh topology, runbook và recovery path đã được support chính thức.**
6. **PR thêm credential lifecycle phải dựa trên write surfaces, audit trail và access semantics đã rõ.**
7. **PR thêm outbound automation phải tái sử dụng durability, retry và visibility semantics đã có thay vì mở một kênh best-effort riêng.**
8. **PR thêm governance/conformance chỉ được claim những phần repo thật sự test, smoke và demo được.**
9. **Ưu tiên theo luồng dùng thật:** release/support baseline rõ → deploy/upgrade path sạch → operator day-2 usable → credentials thật → outbound automation → contract/support policy rõ.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR49 → PR50 → PR51 → PR52 → PR53 → PR54**

Không có PR nào bị cô lập:
- **PR49** khóa release/support baseline cho V6 để mọi docs, smoke path và support assumptions sau đó có mốc rõ
- **PR50** làm sạch đường triển khai/nâng cấp để PR51 có thể mô tả operator workflow trên đúng topology được support
- **PR51** làm rõ triage/recovery workflow để PR52 gắn credential lifecycle vào các action và failure paths thật
- **PR52** làm rõ principal/scope/revoke semantics để PR53 mở outbound automation mà không dựa vào token dùng chung mơ hồ
- **PR53** ổn định external push path để PR54 khóa versioning, support policy và conformance trên đúng surface thực sự được support

---

## 4. Danh sách PR theo thứ tự triển khai

## PR49. V6 release closure và support baseline

**Phụ thuộc:** PR48  
**Dựa trên tasks:** F47  
**Mục tiêu:** chốt V6 thành release/support baseline rõ với version, notes, smoke path và support assumptions

### Bao gồm
- version bump và release metadata cho V6
- release notes / upgrade notes cho runtime, RBAC, streaming và interop baseline của V6
- docs đồng bộ giữa `README.md`, `docs/planning/STATUS.md`, deployment/runbook và release notes
- support assumptions, trust model và supported profile được ghi rõ
- release checklist và smoke verification cho supported profile chính

### Không bao gồm
- deploy topology mới lớn
- operator UX redesign
- credential lifecycle mới

### Điều kiện merge
- có release notes rõ cho V6
- smoke/release verification chạy lại được theo docs
- supported profile và support assumptions không mâu thuẫn nhau giữa các tài liệu chính
- V6 có thể được chỉ ra như baseline bàn giao nội bộ hoặc early-adopter baseline

### Demo sau PR
- tạo release candidate cục bộ hoặc nội bộ cho V6 và chạy lại checklist từ package đến smoke flow trên supported profile đã chốt

---

## PR50. Team deployment ergonomics và upgrade path

**Phụ thuộc:** PR49  
**Dựa trên tasks:** F48  
**Mục tiêu:** làm sạch đường dựng, nâng cấp, backup và rollback cho durable team profile

### Bao gồm
- durable deployment bundle, compose path hoặc topology guide gọn hơn
- env templates, config validation và bootstrap checklist rõ hơn
- upgrade, backup/restore và rollback drills cho supported profile
- readiness/health/smoke path đồng bộ với topology được support
- tests và docs cho deployment assumptions, worker/runtime boundary và failure drill cơ bản

### Không bao gồm
- multi-environment cloud matrix lớn
- autoscaling hoặc distributed scheduler
- operator workflow polish lớn

### Điều kiện merge
- có ít nhất một durable team profile boot được sạch theo docs
- smoke path, readiness path và env template khớp nhau
- upgrade/rollback path tối thiểu chạy lại được hoặc mô tả đủ rõ để lặp lại
- tests deployment/recovery liên quan pass

### Demo sau PR
- dựng supported profile từ env template, chạy smoke, thực hiện một drill nâng cấp hoặc rollback tối thiểu rồi xác nhận hệ thống vẫn sẵn sàng

---

## PR51. Operator console polish và incident workflow

**Phụ thuộc:** PR50  
**Dựa trên tasks:** F49  
**Mục tiêu:** nâng operator surface từ console tối thiểu thành công cụ đủ dùng cho triage, recovery và incident handling hằng ngày

### Bao gồm
- triage views rõ hơn cho sessions, jobs, runtime, queued work và activity
- hiển thị actor/audit/error/reason context tốt hơn
- recovery affordances rõ hơn cho retry/resume/cancel/replay path
- incident timeline hoặc grouping tối thiểu cho việc đọc diễn biến
- docs và runbook bám theo operator workflow thật

### Không bao gồm
- product dashboard lớn
- analytics BI
- kiến trúc frontend mới tách khỏi control plane

### Điều kiện merge
- operator có ít nhất một flow triage → điều tra → recovery rõ ràng qua UI hoặc API support
- lỗi, audit context và reason được hiển thị đủ để người vận hành không phải suy luận từ log thô
- runbook/troubleshooting khớp với UI affordances thực tế
- regression tests cho operator surface không vỡ

### Demo sau PR
- tạo một sự cố nhỏ có chủ đích, dùng operator console để lần theo activity, xác định nguyên nhân, thực hiện recovery và quan sát audit trail tương ứng

---

## PR52. Integration credentials và access lifecycle

**Phụ thuộc:** PR51  
**Dựa trên tasks:** F50  
**Mục tiêu:** cung cấp principal và credential lifecycle tối thiểu nhưng thật cho integration clients

### Bao gồm
- integration principal hoặc service account tối thiểu
- token issue / rotate / revoke / expire semantics
- scoped permissions cho public/operator write surfaces liên quan
- audit enrichment và troubleshooting cho credential usage/failures
- docs cho bootstrap, trust assumptions và migration từ trusted/local path nếu cần

### Không bao gồm
- enterprise SSO hoặc OIDC federation
- self-service IAM portal lớn
- multi-organization identity model

### Điều kiện merge
- có ít nhất một credential flow hoạt động end-to-end cho integration client
- rotate/revoke hoặc expire path được kiểm chứng và có audit rõ
- scope checks chặn được ít nhất các thao tác sai quyền chính
- backward path cho local/trusted flow được giữ hoặc giới hạn rõ trong docs

### Demo sau PR
- tạo một integration principal, gọi một supported write/read path thành công, sau đó rotate hoặc revoke credential và chứng minh request cũ bị từ chối đúng cách

---

## PR53. Outbound integration automation

**Phụ thuộc:** PR52  
**Dựa trên tasks:** F51  
**Mục tiêu:** mở đường push thực dụng để coordinator gửi sự kiện ra ngoài qua webhook hoặc outbound event sink tối thiểu

### Bao gồm
- webhook delivery hoặc outbound event push tối thiểu
- authenticity/signature checks cho outbound requests
- retry, dedupe, failure visibility và replay expectations cơ bản
- sample receiver, docs và troubleshooting cho adopter
- audit trail và operator visibility cho outbound delivery path

### Không bao gồm
- iPaaS builder đầy đủ
- adapter cho nhiều third-party system cùng lúc
- distributed event bus lớn

### Điều kiện merge
- có ít nhất một outbound delivery path hoạt động end-to-end
- failure/retry path hiển thị rõ cho operator hoặc logs/audit support
- docs mô tả rõ signature, retry assumptions và idempotency expectations
- tests delivery/retry pass trên phạm vi đã claim

### Demo sau PR
- chạy một sample receiver cục bộ, phát sinh sự kiện từ coordinator, quan sát webhook được gửi ra, rồi mô phỏng lỗi receiver để chứng minh retry và visibility hoạt động đúng

---

## PR54. Contract governance và early-adopter conformance

**Phụ thuộc:** PR53  
**Dựa trên tasks:** F52  
**Mục tiêu:** chốt versioning, support policy, deprecation semantics và conformance path cho external surface được support

### Bao gồm
- versioning notes cho public API, public events và outbound integrations được support
- support matrix, support window và deprecation semantics tối thiểu
- conformance fixtures, adopter checklist hoặc contract verification path
- docs đồng bộ giữa internal model, external contract và operational assumptions
- V7 release candidate notes dựa trên đúng tập claims đã khóa

### Không bao gồm
- ecosystem-wide guarantees
- nhiều official SDK song song
- broad enterprise support claims vượt quá phạm vi test

### Điều kiện merge
- docs/versioning/support claims không over-claim so với test coverage
- contract tests hoặc conformance fixtures chạy được trên surface được support
- adopter có ít nhất một đường verify rõ theo docs mà không phải đọc sâu vào code
- V7 release candidate đủ rõ để verify nội bộ hoặc early-adopter handoff

### Demo sau PR
- dùng adopter checklist hoặc conformance fixture để xác minh một external client trên đúng supported surface và đối chiếu lại với compatibility/support matrix

---

## 5. Mốc giá trị sau từng PR

### Mốc Y — sau PR49
Bạn có:
- V6 được chốt thành release/support baseline rõ
- versioning, release notes và smoke path đồng bộ hơn

### Mốc Z — sau PR50
Bạn có:
- một durable deployment path sạch hơn và dễ lặp lại hơn
- upgrade/rollback assumptions rõ hơn cho nhóm khác

### Mốc AA — sau PR51
Bạn có:
- operator console đủ dùng hơn cho triage và recovery hằng ngày
- runbook bám sát hơn với control surface thật

### Mốc AB — sau PR52
Bạn có:
- integration principal và credential lifecycle tối thiểu nhưng thật
- access model bớt phụ thuộc vào trusted path mơ hồ

### Mốc AC — sau PR53
Bạn có:
- đường outbound push thực dụng cho external workflows
- visibility tốt hơn cho delivery failure và retry

### Mốc AD — sau PR54
Bạn có:
- compatibility/support surface hẹp nhưng có versioning và conformance path rõ
- nền đủ sạch để bước sang V8 hardening có chọn lọc hoặc wider adoption có kiểm soát

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:
- `pr/49-v6-release-support-baseline`
- `pr/50-team-deployment-ergonomics`
- `pr/51-operator-incident-workflow`
- `pr/52-integration-credentials`
- `pr/53-outbound-automation`
- `pr/54-contract-governance`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:
- code chạy được local hoặc trên supported profile liên quan
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- release/deploy/auth/webhook/support claims không mập mờ
- có ít nhất một cách demo thủ công
- không mở rộng phạm vi PR quá đà

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự **PR49 → PR54**
- không nhảy sang PR52 hoặc PR53 nếu PR49-PR51 chưa khóa xong baseline support, deploy và operator workflow

Nếu bạn làm theo sprint:
- có thể gộp **PR49 + PR50** thành một sprint chốt baseline release và đường triển khai
- có thể gộp **PR52 + PR53** thành một sprint tập trung external integration path
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `docs/planning/archive/PLAN_V7.md`:
- `docs/planning/archive/PLAN_V7.md` trả lời câu hỏi: **phase V7 nhằm giải quyết vấn đề gì**
- `docs/planning/archive/IMPLEMENTATION_ORDER_V7.md` trả lời câu hỏi: **nên merge theo thứ tự nào**
