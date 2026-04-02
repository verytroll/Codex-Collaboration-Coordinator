# PLAN_V8.md

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi V7 release closure đã hoàn tất tại F53 / PR55.

Khác với `docs/planning/archive/PLAN_V7.md`:

* `docs/planning/archive/PLAN_V7.md` tập trung đưa hệ thống từ mức “control plane dùng được và đã kiểm chứng” sang mức “early-adopter product” với release baseline, deploy path, operator workflow, credential lifecycle và contract governance rõ hơn
* `docs/planning/PLAN_V8.md` tập trung đưa hệ thống từ mức “early-adopter baseline đã bàn giao” sang mức “long-running small-team baseline” với data lifecycle rõ hơn, observability bền hơn, guardrails chặt hơn và trust model sạch hơn cho vận hành dài ngày

Tài liệu này kế thừa và nên đọc cùng:

* `README.md`
* `docs/planning/STATUS.md`
* `docs/planning/archive/PLAN_V7.md`
* `docs/reference/PRD.md`
* `docs/reference/ARCHITECTURE.md`
* `docs/reference/API.md`
* `docs/reference/DB_SCHEMA.md`
* `docs/operations/DEPLOYMENT.md`
* `docs/operations/RUNBOOK.md`
* `docs/operations/OBSERVABILITY.md`
* `docs/operator/OPERATOR_UI.md`
* `docs/integrations/a2a/A2A_PUBLIC_API.md`
* `docs/integrations/a2a/A2A_PUBLIC_EVENTS.md`
* `docs/integrations/a2a/A2A_COMPATIBILITY_MATRIX.md`
* `docs/releases/RELEASE_NOTES_V7.md`
* `docs/releases/UPGRADE_NOTES_V7.md`

* * *

## 2. Điểm xuất phát của V8

Sau V7, hệ thống đã có:

* release baseline `0.4.0` rõ ràng với release gate, package bundle và early-adopter handoff path lặp lại được
* operator workflow đủ dùng cho triage, recovery và incident nhỏ hằng ngày
* managed integration credentials với rotate / revoke / expire semantics cơ bản
* managed outbound webhooks cho public A2A task events, có retry, recovery và visibility cơ bản
* public/A2A surface được quản trị bởi compatibility matrix, conformance script và contract tests
* packaged `small-team` deployment path đủ rõ để nhóm khác cài đặt, smoke và bàn giao

Điểm còn thiếu để đi tiếp:

* telemetry hiện vẫn chủ yếu là in-memory process state; sau restart hoặc handoff dài ngày, operator thiếu lịch sử bền để đọc incident theo thời gian
* retention, archive, cleanup và lifecycle policy cho session/activity/public events/webhook deliveries/artifacts chưa được chốt thành một discipline rõ cho môi trường chạy lâu ngày
* external surfaces đã có replay, SSE và webhooks nhưng quota, rate limiting, retention window, slow-consumer và backpressure semantics vẫn chưa được khóa thành support baseline rõ
* managed credentials đã có, nhưng bootstrap token và header-based actor path vẫn còn mang tính legacy/compatibility khá rộng; trust model cho long-running deployment chưa đủ sạch
* operator surface đã tốt cho triage/recovery, nhưng maintenance workflows như archive, cleanup, credential hygiene, webhook hygiene và periodic operational drills vẫn chưa thành một bề mặt làm việc rõ ràng
* V7 đủ cho early-adopter handoff, nhưng chưa đủ cứng để tuyên bố một baseline “chạy lâu ngày cho nhóm nhỏ” mà không bổ sung guardrails và lifecycle discipline

* * *

## 3. Mục tiêu của V8

V8 nên làm rõ 6 hướng:

1. Biến baseline V7 từ “early-adopter handoff được” thành “long-running small-team deployment dùng được” với lifecycle rõ hơn.
2. Chốt data lifecycle cho session, activity, artifacts, public events, webhook deliveries và telemetry theo hướng archive-first, cleanup có kiểm soát.
3. Nâng observability từ mức process-local live view sang mức có incident/history đủ bền cho restart, handoff và debugging theo thời gian.
4. Bổ sung guardrails rõ cho external/operator surfaces: rate limiting, replay window, slow-consumer expectations, webhook fanout/delivery limits và failure semantics.
5. Siết trust model theo hướng managed credentials là path chính, thu hẹp dần bootstrap/legacy paths thay vì mở rộng thêm.
6. Chốt V8 thành một release/support baseline rõ cho small-team dùng lâu ngày, nhưng vẫn tránh nhảy sang distributed hoặc enterprise platform quá sớm.

* * *

## 4. Phạm vi của V8

### 4.1 Trong phạm vi

V8 ưu tiên các hướng sau:

1. data lifecycle và retention discipline:
   * archive/cleanup semantics cho session và session-adjacent data
   * retention policy cho activity, telemetry, public events và webhook deliveries
   * export-before-prune hoặc audit-preserving cleanup path khi cần
   * operator visibility cho retention/cleanup state
2. durable observability và incident history:
   * lưu lại signal/summary quan trọng đủ bền sau restart
   * correlation tốt hơn giữa request, session, job, runtime, task và delivery
   * history/debug path phù hợp cho handoff và troubleshooting dài ngày
3. external surface guardrails:
   * rate limiting hoặc quota guardrails nhẹ nhưng rõ
   * replay/stream/webhook retention window và slow-consumer semantics
   * error/status mapping rõ khi client vượt giới hạn hoặc rơi ngoài supported window
4. trust tightening và auth hygiene:
   * managed credentials là supported external path rõ ràng hơn
   * bootstrap shared token bị thu hẹp về bootstrap/compatibility use cases
   * actor/service identity semantics rõ hơn cho write flows dài ngày
5. operator maintenance workflows:
   * archive, cleanup, rotate/revoke/disable, recovery drill, hygiene checks
   * runbook và UI/debug/dashboard bám sát maintenance path thật
6. release closure cho V8:
   * release notes / upgrade notes
   * support assumptions cho long-running small-team baseline
   * package/release/conformance gates đồng bộ với guardrails và lifecycle mới

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V8:

* enterprise SSO, OIDC federation hoặc IAM phức tạp
* multi-tenant hosted SaaS control plane
* distributed multi-node scheduler, multi-region coordinator hoặc event bus platform
* broad Kubernetes / cloud deployment matrix
* official SDK matrix cho nhiều ngôn ngữ
* web product hoàn chỉnh cho end user ngoài operator/integrator
* thay packaged baseline khỏi `small-team` + SQLite như supported default chính thức
* thay coordinator-first model bằng kiến trúc mới song song

* * *

## 5. Nguyên tắc triển khai cho V8

1. Long-running use trước broader expansion. Trước khi mở thêm adoption claims, phải làm rõ retention, cleanup, guardrails và incident history cho baseline hiện có.

2. Archive-first thay vì delete-first. Dữ liệu vận hành nên có đường archive/export/audit rõ trước khi có cleanup cứng.

3. Guardrails phải giải thích được. Rate limit, quota, retention window hay disable path chỉ có giá trị nếu operator/client nhìn thấy lý do và cách phục hồi tương ứng.

4. Managed credentials là đường chính. V8 không mở rộng thêm legacy shared-token semantics; nếu có compatibility path thì phải ghi rõ là compatibility-only.

5. Observability phải bền đủ cho handoff. Tối thiểu các incident summary, failure hotspots và delivery/auth anomalies không nên mất hoàn toàn sau restart.

6. Giữ packaged `small-team` path sạch trước. Không thêm profile support mới nếu baseline hiện có chưa đủ dễ vận hành dài ngày.

7. PR nhỏ, boundary rõ. Không gộp retention, observability, trust hardening, guardrails và release closure vào một PR lớn khó rollback.

* * *

## 6. Trình tự triển khai cấp cao

Dự án ở V8 nên đi qua 6 giai đoạn:

**G38 → G39 → G40 → G41 → G42 → G43**

Trong đó:

* G38 chốt data lifecycle và retention discipline
* G39 làm bền observability và incident history
* G40 thêm external surface guardrails và flow-control semantics
* G41 siết trust model và thu hẹp legacy bootstrap paths
* G42 mở operator maintenance workflows và hygiene automation
* G43 chốt release/support baseline cho long-running small-team deployment

Phụ thuộc:

* G39 phụ thuộc G38 vì observability history nên bám đúng lifecycle/retention model đã chốt, tránh lưu bền một đống signal mà chưa có cleanup policy
* G40 phụ thuộc G39 vì guardrails và slow-consumer semantics cần surface quan sát đủ rõ để giải thích throttle, drop hoặc retention misses
* G41 phụ thuộc G40 vì trust tightening nên chạy trên external surface đã có giới hạn và failure semantics rõ
* G42 phụ thuộc G41 vì maintenance workflows phải phản ánh đúng auth model, retention jobs và guardrails cuối cùng
* G43 phụ thuộc G42 vì release/support claims chỉ nên khóa sau khi lifecycle, observability, guardrails và maintenance paths đều đã kiểm chứng

* * *

## 7. Kế hoạch chi tiết theo giai đoạn

## G38. Data lifecycle và retention discipline

Phụ thuộc: F53 / PR55  
Mở khóa: G39  
Kết quả: hệ thống có policy rõ cho archive, retention, cleanup và export của các surface vận hành chính

Bao gồm:

* lifecycle policy cho session, session activity, transcript exports, artifacts, public events, subscriptions, webhook deliveries và telemetry snapshots nếu có
* cấu hình retention window hoặc cleanup cadence đủ rõ cho packaged baseline
* operator/debug visibility tối thiểu cho backlog cleanup, archived state và items nằm ngoài retention window
* docs cho archive, cleanup, backup-before-prune và các giả định không xóa cứng bừa bãi

Không bao gồm:

* data warehouse lớn
* legal hold hay compliance stack đầy đủ
* UI analytics cho dữ liệu lịch sử

## G39. Durable observability và incident history

Phụ thuộc: G38  
Mở khóa: G40  
Kết quả: operator có history/debug surface bền hơn cho restart, handoff và điều tra incident theo thời gian

Bao gồm:

* persistence hoặc export path cho telemetry/incident summaries quan trọng thay vì chỉ giữ in-memory live state
* correlation rõ hơn giữa request, session, job, runtime, task, credential và outbound delivery
* history views hoặc debug payload đủ để đọc recent incidents sau restart
* docs/runbook cho incident reading, signal interpretation và retention assumptions của history surface

Không bao gồm:

* BI dashboard lớn
* metrics pipeline enterprise
* full-text observability platform tách rời

## G40. External surface guardrails và flow control

Phụ thuộc: G39  
Mở khóa: G41  
Kết quả: public/operator/external surfaces có giới hạn và failure semantics rõ hơn cho dùng thật dài ngày

Bao gồm:

* rate limiting hoặc quota guardrails nhẹ cho supported external paths khi phù hợp
* replay/SSE retention window, slow-consumer và cursor-gap semantics rõ hơn
* webhook registration/delivery guardrails như delivery limits, retry visibility và expectations khi receiver chậm hoặc lỗi lặp
* contract/docs/tests/conformance notes cập nhật theo đúng guardrails đã mở

Không bao gồm:

* API gateway platform riêng
* distributed streaming infrastructure
* broad marketplace guarantees cho external clients

## G41. Trust tightening và legacy path minimization

Phụ thuộc: G40  
Mở khóa: G42  
Kết quả: supported trust model sạch hơn cho long-running deployment, với managed credentials là external path mặc định

Bao gồm:

* dọn claim và behavior quanh shared `ACCESS_TOKEN`, actor headers và managed credentials
* giảm phạm vi supported của bootstrap/legacy paths khi hợp lý, nhưng vẫn giữ local/dev compatibility cần thiết
* credential hygiene tốt hơn cho rotate/revoke/expire/disable flows và failure explanations
* migration notes rõ cho operator và integrator nếu có thay đổi trust assumptions

Không bao gồm:

* enterprise identity federation
* self-service IAM portal lớn
* user directory hoặc organization model mới

## G42. Operator maintenance workflows và hygiene automation

Phụ thuộc: G41  
Mở khóa: G43  
Kết quả: operator surface đủ dùng cho maintenance định kỳ, không chỉ triage và recovery khi sự cố đã xảy ra

Bao gồm:

* archive/cleanup/retry/disable/rotate workflows rõ cho session data, credentials và outbound integrations
* hygiene views hoặc summaries cho retention jobs, expired credentials, disabled integrations và stale runtime state
* runbook/troubleshooting bám theo maintenance operations thật
* tests cho maintenance happy path, failure path và guardrail path

Không bao gồm:

* product UI lớn cho admin ngoài phạm vi operator
* policy automation quá rộng ngoài các hygiene workflows chính
* managed integration marketplace

## G43. Release closure và support baseline cho V8

Phụ thuộc: G42  
Mở khóa: phase sau V8  
Kết quả: V8 trở thành một baseline “long-running small-team” rõ ràng, có version, package, notes và claims support phù hợp

Bao gồm:

* release notes, upgrade notes và version bump cho V8
* release gate, package manifest, smoke path và conformance path đồng bộ với lifecycle/guardrails/trust model mới
* support assumptions cho long-running small-team deployment và controlled wider adoption
* docs/status/readme không drift khỏi baseline release thật

Không bao gồm:

* broad enterprise support commitments
* nhiều supported deployment profile cạnh tranh nhau
* rebrand lớn của sản phẩm hoặc package surface

* * *

## 8. Kết quả mong đợi sau V8

Nếu V8 hoàn tất tốt, hệ thống nên đạt trạng thái sau:

1. `small-team` không chỉ là packaged baseline có thể handoff, mà là baseline có thể chạy lâu ngày với retention và maintenance discipline rõ.
2. Operator có thể đọc incident gần đây và failure hotspots ngay cả sau restart hoặc handoff ca trực.
3. External clients gặp giới hạn hay retention gap sẽ nhận semantics rõ hơn thay vì hành vi mơ hồ.
4. Managed credentials trở thành trust path sạch và rõ hơn cho integrator; legacy bootstrap path bị thu hẹp đúng mức.
5. Session/activity/artifact/public-event/webhook data có lifecycle rõ, tránh phình dữ liệu và giảm rủi ro debug trên dữ liệu rác.
6. Repo có một V8 release baseline đủ chắc để nghĩ tới adoption rộng hơn hoặc hạ tầng mạnh hơn ở phase sau, mà không cần quay lại dọn debt vận hành cơ bản.

* * *

## 9. Rủi ro chính của V8

1. Mở guardrails quá mạnh mà không có operator visibility sẽ làm client/operator thấy hệ thống “bị chặn ngẫu nhiên”.
2. Thêm observability persistence mà không chốt retention sẽ chỉ chuyển vấn đề từ “mất dữ liệu” sang “phình dữ liệu”.
3. Thu hẹp legacy auth path quá nhanh mà không có migration notes và runbook rõ sẽ làm adopter hiện tại gãy flow.
4. Gom retention, guardrails, auth hardening và operator maintenance vào một PR lớn sẽ làm review/rollback khó kiểm soát.
5. Đòi hỏi quá nhiều profile deployment mới trong V8 sẽ làm baseline `small-team` hiện có mất độ sạch vừa đạt ở V7.
6. Nâng claim support nhanh hơn tốc độ test/smoke/conformance sẽ làm trust vào docs và release baseline giảm trở lại.

* * *

## 10. Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. data lifecycle và retention discipline
2. durable observability và incident history
3. external surface guardrails và flow control
4. trust tightening và legacy path minimization
5. operator maintenance workflows
6. V8 release closure mở rộng hơn mức tối thiểu

* * *

## 11. Cách dùng tài liệu này

Nếu bạn làm một mình:

* đi theo đúng thứ tự G38 → G43
* không mở adoption claims mới trước khi retention, history và guardrails của baseline hiện tại đủ rõ
* không biến operator maintenance thành một bài toán product UI rộng ngoài control-plane needs

Nếu bạn làm theo sprint:

* có thể gộp G38 + G39 thành một sprint “long-running lifecycle + observability foundation”
* có thể gộp G40 + G41 thành một sprint “external guardrails + trust tightening”
* nhưng vẫn nên giữ merge/review theo PR nhỏ tách biệt giữa lifecycle, observability, guardrails, auth, maintenance và release closure

Nếu bạn dùng cùng các tài liệu triển khai tiếp theo:

* `docs/planning/PLAN_V8.md` trả lời câu hỏi: phase V8 nhằm giải quyết vấn đề gì
* `docs/planning/IMPLEMENTATION_TASKS_V8.md` nên trả lời câu hỏi: cần làm cụ thể những gì để hoàn tất từng feature slice của V8
* `docs/planning/IMPLEMENTATION_ORDER_V8.md` nên trả lời câu hỏi: nên merge các PR theo thứ tự nào để giữ baseline ổn định
