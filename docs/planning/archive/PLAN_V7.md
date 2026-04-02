# PLAN_V7.md

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi V6 implementation đã hoàn tất tại F46 / PR48.

Khác với `docs/planning/archive/PLAN_V6.md`:

* `docs/planning/archive/PLAN_V6.md` tập trung đưa hệ thống từ mức “small-team usable” sang mức “team operations / production control plane” với action surface, RBAC cơ bản, durable runtime, streaming và interop certification
* `docs/planning/archive/PLAN_V7.md` tập trung đưa hệ thống từ mức “control plane dùng được và đã kiểm chứng” sang mức “early-adopter product” với release/support baseline rõ hơn, đường cài đặt/nâng cấp gọn hơn, operator workflow thực dụng hơn và contract external được quản trị rõ hơn

Tài liệu này kế thừa và nên đọc cùng:

* `docs/reference/PRD.md`
* `docs/reference/ARCHITECTURE.md`
* `docs/reference/API.md`
* `docs/reference/DB_SCHEMA.md`
* `README.md`
* `docs/planning/archive/PLAN.md`
* `docs/planning/archive/PLAN_V2.md`
* `docs/planning/archive/PLAN_V3.md`
* `docs/planning/archive/PLAN_V4.md`
* `docs/planning/archive/PLAN_V5.md`
* `docs/planning/archive/PLAN_V6.md`
* `docs/planning/STATUS.md`
* `docs/operations/DEPLOYMENT.md`
* `docs/operations/RUNBOOK.md`
* `docs/operator/OPERATOR_UI.md`
* `docs/operations/OBSERVABILITY.md`
* `docs/integrations/a2a/A2A_PUBLIC_API.md`
* `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`
* `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`
* `docs/integrations/a2a/A2A_QUICKSTART.md`

* * *

## 2. Điểm xuất phát của V7

Sau V6, hệ thống đã có:

* coordinator-first core đã đi qua lộ trình từ MVP tới control plane rõ ràng thay vì dừng ở A2A adapter thử nghiệm
* operator action surface tối thiểu với approve/reject/retry/resume/cancel cùng audit trail theo actor
* identity và team RBAC mức cơ bản cho operator, reviewer và integration client
* durable runtime và persistence boundary tốt hơn, đủ cho small-team hoặc team deployment thực tế hơn
* realtime streaming transport với SSE resume semantics cho operator activity và public task events
* public/A2A compatibility surface hẹp nhưng đã có contract tests, compatibility matrix và adoption notes

Điểm còn thiếu để đi tiếp:

* V6 mới dừng ở mức implementation hoàn tất và release candidate đủ mạnh; repo vẫn thiếu một pha chốt V6 thành baseline support/release rõ như một sản phẩm nội bộ có thể bàn giao cho nhóm khác
* operator surface đã thao tác được nhưng vẫn còn thiên về “minimal control console”; triage, recovery, incident handling và giải thích lỗi cho day-2 operations chưa đủ mượt
* đường triển khai durable profile vẫn còn mang hơi hướng “người hiểu repo sẽ dựng được”; người mới vẫn có thể phải đọc code hoặc nhiều docs rời để bootstrap, backup, upgrade và rollback
* access model hiện đủ cho trusted/team environment cơ bản nhưng credential lifecycle cho integration client vẫn còn mỏng, chưa đủ rõ cho rotate/revoke/expire và quản trị service account tối thiểu
* external integrations hiện có polling, replay và streaming, nhưng nhiều adopter thực tế sẽ cần outbound push đơn giản hơn kiểu webhook để nối vào workflow sẵn có mà không giữ kết nối lâu dài
* compatibility claims đã đáng tin hơn trước, nhưng versioning, support window, deprecation semantics và conformance path cho adopter vẫn chưa được đóng thành một discipline riêng

* * *

## 3. Mục tiêu của V7

V7 nên làm rõ 6 hướng:

1. Chốt V6 thành release/support baseline thật để làm mốc ổn định cho adopter đầu tiên.
2. Nâng operator surface từ mức “thao tác được” sang mức “day-2 operations usable” cho triage, recovery và incident workflow.
3. Làm đường cài đặt, nâng cấp và khôi phục cho durable team profile đủ rõ để một nhóm khác có thể tự dựng mà không cần suy luận nhiều từ code.
4. Mở access model từ RBAC cơ bản sang credential lifecycle tối thiểu nhưng thật cho integration clients và service accounts.
5. Bổ sung outbound integration path thực dụng để hệ thống dễ cắm vào workflow ngoài hơn, thay vì chỉ dựa vào polling hoặc streaming.
6. Chốt versioning, support policy và conformance path cho public/A2A surface để mở adoption rộng hơn nhưng vẫn giữ claim hẹp và đáng tin.

* * *

## 4. Phạm vi của V7

### 4.1 Trong phạm vi

V7 ưu tiên các hướng sau:

1. release closure và support baseline cho V6:
   * release notes cho V6
   * upgrade notes / migration notes cho auth, durable profile và streaming path
   * version tag strategy và release manifest rõ hơn
   * smoke/release verification cho ít nhất một supported deployment path
   * support assumptions và compatibility scope được ghi rõ
2. operator console polish và incident workflow:
   * triage views rõ hơn cho session/job/runtime/activity
   * hiển thị audit, actor context và error explanations tốt hơn
   * recovery affordances thực dụng hơn cho restart/retry/resume/cancel path
   * runbook gắn sát với operator workflow thật
3. team deployment ergonomics:
   * durable deployment bundle hoặc topology guide gọn hơn
   * env templates và bootstrap path rõ hơn
   * backup/restore/upgrade/rollback drills rõ hơn
   * smoke path và readiness path khớp với supported profile thật
4. integration credentials và access lifecycle:
   * integration principal hoặc service account tối thiểu
   * token issue / rotate / revoke / expire semantics
   * scoped permissions đủ nhỏ cho public/operator write paths liên quan
   * audit trail và troubleshooting cho credential failures
5. outbound integration automation:
   * webhook delivery hoặc outbound event push tối thiểu
   * delivery signature / authenticity checks
   * retry, dedupe, failure visibility và replay expectations
   * docs và sample receiver cho adopter
6. contract governance và conformance path:
   * versioning notes cho public/A2A surface
   * deprecation policy hẹp nhưng rõ
   * support matrix và support window tối thiểu
   * conformance fixtures hoặc contract verification path cho adopter

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V7:

* enterprise SSO đầy đủ, OIDC federation hoặc IAM phức tạp
* multi-tenant hosted SaaS control plane hoàn chỉnh
* distributed multi-node scheduler hoặc multi-region coordinator
* Kubernetes hoặc cloud-platform matrix rộng cho nhiều môi trường cùng lúc
* marketplace plugin ecosystem
* web product hoàn chỉnh cho end user ngoài operator/integrator
* bộ SDK chính thức cho nhiều ngôn ngữ cùng lúc
* thay coordinator-first model bằng A2A-first hoặc event-bus-first architecture mới

* * *

## 5. Nguyên tắc triển khai cho V7

1. Productization trước expansion. Chỉ mở thêm surface adoption mới khi release, install, runbook và support baseline của surface hiện có đã đủ rõ.

2. Coordinator-first vẫn giữ nguyên. V7 không tạo một control model mới song song với `session/job/artifact/review/runtime`; mọi polish và externalization phải bám lên internal model hiện có.

3. Day-2 operations quan trọng ngang day-0 setup. Một tính năng chỉ hữu ích cho adopter nếu người vận hành biết quan sát, khôi phục, giải thích lỗi và rollback khi có sự cố.

4. Credential lifecycle phải tối giản nhưng thật. Không cần enterprise IAM, nhưng bất kỳ đường external write nào được mở thêm đều cần principal rõ, scope rõ và đường rotate/revoke rõ.

5. Outbound automation phải kế thừa durability đã có. Webhook hoặc event push mới phải dựa trên queue/retry/recovery semantics hiện có thay vì tạo một kênh best-effort mơ hồ ngoài luồng.

6. Contract governance phải đi cùng test và docs. Không tuyên bố support window, versioning hay deprecation semantics cho phần mà repo chưa kiểm chứng được bằng smoke path, contract tests hoặc sample flow.

7. Giữ một supported path sạch trước khi nhân rộng. Tốt hơn là có một durable deployment path và một adoption path được viết rõ, hơn là nhiều profile nửa vời cạnh tranh nhau.

8. PR nhỏ, boundary rõ. Không gộp operator polish, deploy ergonomics, credential lifecycle, webhooks và governance vào một PR lớn khó review.

* * *

## 6. Trình tự triển khai cấp cao

Dự án ở V7 nên đi qua 6 giai đoạn:

G32 → G33 → G34 → G35 → G36 → G37

Trong đó:

* G32 chốt release/support baseline cho V6
* G33 làm sạch đường triển khai và nâng cấp cho durable team profile
* G34 nâng operator console từ mức tối thiểu lên mức day-2 operations usable
* G35 thêm integration credentials và access lifecycle tối thiểu
* G36 mở outbound integration automation theo hướng webhook/event push thực dụng
* G37 khóa versioning, support policy và conformance path cho adopter

Phụ thuộc:

* G33 phụ thuộc G32 vì deployment guide, smoke path và support assumptions nên bám trên một release baseline đã chốt
* G34 phụ thuộc G33 vì operator workflow, runbook và recovery expectations nên phản ánh đúng topology hỗ trợ chính thức thay vì một môi trường cục bộ ngẫu nhiên
* G35 phụ thuộc G34 vì credential lifecycle chỉ có ý nghĩa khi các operator/public write surfaces và recovery path đã đủ rõ cho người vận hành
* G36 phụ thuộc G35 vì outbound integration path nên chạy trên principal, scope và audit semantics đã rõ thay vì dựa vào token dùng chung mơ hồ
* G37 phụ thuộc G36 vì version/support/conformance policy nên khóa trên đúng tập external surface đã thật sự mở và kiểm chứng được

* * *

## 7. Kế hoạch chi tiết theo giai đoạn

## G32. Release closure và support baseline cho V6

Phụ thuộc: G31 / F46  
Mở khóa: G33  
Kết quả: V6 không chỉ “implementation complete” mà trở thành một baseline release/support rõ cho adopter đầu tiên

Bao gồm:

* release notes cho V6
* upgrade notes / migration notes cho durable runtime, RBAC và streaming
* version bump, release tag strategy và release manifest sạch hơn
* smoke/release verification cho supported profile chính
* support assumptions, trust model và scope claims được đồng bộ vào docs chính

Không bao gồm:

* operator UX redesign lớn
* credential lifecycle mới
* surface integration mới

## G33. Team deployment ergonomics và upgrade path

Phụ thuộc: G32  
Mở khóa: G34  
Kết quả: một nhóm khác có thể dựng, nâng cấp và khôi phục durable profile mà không cần đọc sâu vào code để suy luận topology

Bao gồm:

* durable deployment bundle, compose path hoặc topology guide gọn và rõ
* env templates, bootstrap checklist và secret/config expectations
* backup/restore/upgrade/rollback notes rõ hơn
* smoke path bám đúng supported profile
* docs cho readiness, health, worker/runtime boundary và failure drill cơ bản

Không bao gồm:

* cloud platform đa môi trường
* autoscaling phức tạp
* orchestration lại toàn bộ deployment model

## G34. Operator console polish và incident workflow

Phụ thuộc: G33  
Mở khóa: G35  
Kết quả: operator surface chuyển từ console tối thiểu sang công cụ đủ dùng hằng ngày cho triage, recovery và vận hành ca sự cố nhỏ

Bao gồm:

* triage views rõ hơn cho sessions, jobs, approvals, runtime và queued work
* hiển thị actor/audit/error/reason ngữ cảnh tốt hơn
* recovery affordances rõ hơn cho retry/resume/cancel/replay path
* timeline hoặc activity grouping tối thiểu cho incident reading
* runbook và troubleshooting notes bám theo flow vận hành thật

Không bao gồm:

* dashboard BI lớn
* analytics product cho end user
* frontend redesign tách khỏi control-plane needs

## G35. Integration credentials và access lifecycle

Phụ thuộc: G34  
Mở khóa: G36  
Kết quả: external integrator có principal và credential model đủ rõ để vận hành thật, thay vì chỉ dựa vào token bootstrap hoặc trusted path mơ hồ

Bao gồm:

* integration principal hoặc service account tối thiểu
* token issue / rotate / revoke / expire semantics
* scoped permissions cho các write/read surfaces liên quan
* audit enrichment cho credential usage và failures
* bootstrap docs, trust assumptions và troubleshooting cho credential lifecycle

Không bao gồm:

* SSO enterprise
* federation giữa nhiều identity provider
* self-service IAM portal lớn

## G36. Outbound integration automation

Phụ thuộc: G35  
Mở khóa: G37  
Kết quả: adopter có một đường nhận tín hiệu hệ thống theo kiểu push thực dụng để nối coordinator vào workflow ngoài mà không buộc giữ stream liên tục

Bao gồm:

* webhook delivery hoặc outbound event sink tối thiểu
* signature hoặc authenticity checks cho request gửi ra ngoài
* retry, dedupe, failure visibility và basic replay expectations
* sample receiver, docs và troubleshooting cho integration mismatch
* audit trail và operator visibility cho outbound delivery path

Không bao gồm:

* iPaaS / workflow builder đầy đủ
* adapter cho hàng loạt third-party systems cùng lúc
* distributed event bus lớn

## G37. Contract governance và early-adopter conformance path

Phụ thuộc: G36  
Mở khóa: phase sau V7  
Kết quả: repo có thể hỗ trợ một compatibility surface hẹp nhưng có version/support policy rõ, đủ sạch để bước sang adoption rộng hơn hoặc hardening có chọn lọc ở V8

Bao gồm:

* versioning notes và deprecation semantics cho public/A2A/external integration surface được support
* support matrix và support window tối thiểu
* conformance fixtures, contract verification path hoặc adopter checklist
* docs đồng bộ giữa internal model, external contract và operational assumptions
* release candidate cho V7 dựa trên đúng tập claims đã khóa

Không bao gồm:

* ecosystem-wide guarantees
* nhiều official SDK song song
* broad enterprise commitments vượt quá phạm vi repo thực sự kiểm chứng

* * *

## 8. Kết quả mong đợi sau V7

Nếu V7 hoàn tất tốt, hệ thống nên đạt trạng thái sau:

1. Có V6 release baseline rõ và V7 support baseline đủ sạch cho adopter đầu tiên.
2. Operator có thể xử lý triage, recovery và incident nhỏ hằng ngày mà ít phải nhảy qua nhiều docs hoặc route rời rạc.
3. Durable deployment path đủ rõ để một nhóm khác có thể tự cài đặt, nâng cấp và rollback với mức đoán tối thiểu.
4. Integration client có credential lifecycle và access model đủ thật để dùng ngoài phạm vi nhóm lõi.
5. External systems có thể tích hợp bằng polling, streaming hoặc outbound push tùy nhu cầu thực tế, nhưng vẫn bám cùng một contract model rõ ràng.
6. Public/A2A/support claims có versioning, deprecation và conformance path đủ hẹp nhưng đáng tin để mở adoption tiếp theo.

* * *

## 9. Rủi ro chính của V7

1. Mở rộng adoption quá nhanh khi release/support baseline cho V6 chưa chốt sẽ làm docs, package và support claims lệch nhau.
2. Làm deployment ergonomics cho quá nhiều topology cùng lúc sẽ khiến không profile nào thực sự sạch và đáng tin.
3. Thêm credential lifecycle nhưng bootstrap path không rõ sẽ làm hệ thống vừa khó dùng vừa dễ cấu hình sai theo hướng mất an toàn.
4. Mở webhook/outbound push mà không có retry, visibility và audit đủ rõ sẽ tạo ra integration failures âm thầm, khó debug hơn streaming hiện có.
5. Để operator console drift thành một product UI rộng thay vì công cụ day-2 operations sẽ làm chậm các mục tiêu productization thực sự quan trọng.
6. Tuyên bố support/version policy rộng hơn phần repo thực sự có tests, smoke path và adopter flow sẽ làm mất độ tin cậy vừa xây được ở V6.

* * *

## 10. Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. release closure và support baseline cho V6
2. team deployment ergonomics và upgrade path
3. operator console polish và incident workflow
4. integration credentials và access lifecycle
5. contract governance và conformance path
6. outbound integration automation

* * *

## 11. Cách dùng tài liệu này

Nếu bạn làm một mình:

* đi theo đúng thứ tự G32 → G37
* không mở adoption surface mới trước khi release/support baseline và install path đủ rõ
* không biến operator polish thành một bài toán product UI rộng ngoài nhu cầu control plane

Nếu bạn làm theo sprint:

* có thể gộp G32 + G33 thành một sprint chốt baseline release và đường dựng hệ thống
* có thể gộp G35 + G36 thành một sprint tập trung external integration path
* nhưng vẫn nên giữ merge/review theo PR nhỏ tách biệt giữa release, deploy, operator, credentials, webhooks và governance

Nếu bạn dùng cùng các tài liệu triển khai tiếp theo:

* `docs/planning/archive/PLAN_V7.md` trả lời câu hỏi: phase V7 nhằm giải quyết vấn đề gì
* `docs/planning/archive/IMPLEMENTATION_ORDER_V7.md` nên trả lời câu hỏi: nên merge các PR theo thứ tự nào
* `docs/planning/archive/IMPLEMENTATION_TASKS_V7.md` nên trả lời câu hỏi: cần làm cụ thể những gì để hoàn tất từng giai đoạn của V7

