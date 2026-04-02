# PLAN_V6.md

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi V5 implementation đã hoàn tất tại F40 / PR42.

Khác với `docs/planning/archive/PLAN_V5.md`:

* `docs/planning/archive/PLAN_V5.md` tập trung mở access boundary tối thiểu, thin operator UI, realtime operator surface, A2A interoperability ban đầu và small-team deployment profile
* `docs/planning/archive/PLAN_V6.md` tập trung đưa hệ thống từ mức “small-team usable” sang mức “team operations / production control plane” với khả năng vận hành thật, thao tác thật, identity rõ hơn và runtime bền hơn

Tài liệu này kế thừa và nên đọc cùng:

* `docs/reference/PRD.md`
* `docs/reference/ARCHITECTURE.md`
* `docs/reference/API.md`
* `docs/reference/DB_SCHEMA.md`
* `docs/planning/archive/PLAN.md`
* `docs/planning/archive/PLAN_V2.md`
* `docs/planning/archive/PLAN_V3.md`
* `docs/planning/archive/PLAN_V4.md`
* `docs/planning/archive/PLAN_V5.md`
* `docs/planning/STATUS.md`
* `docs/operator/OPERATOR_UI.md`
* `docs/operations/DEPLOYMENT.md`
* `docs/integrations/a2a/A2A_MAPPING.md`

* * *

## 2. Điểm xuất phát của V6

Sau V5, hệ thống đã có:

* thin operator UI shell để đọc session, transcript, job, approval, artifact, dashboard summary và replayable activity
* access boundary tối thiểu cho operator/public surface
* realtime operator surface ở mức replay/polling đủ dùng cho small-team operations
* A2A interoperability và adoption kit ban đầu
* deployment profile `small-team` cùng release packaging cho môi trường nhỏ

Điểm còn thiếu để đi tiếp:

* operator UI hiện vẫn là bề mặt đọc trạng thái; local filters không thay đổi orchestration state và chưa có action surface thật cho approve/retry/cancel/resume
* access boundary hiện phù hợp cho môi trường tin cậy nhỏ, chưa đủ rõ ở mức identity người dùng, team role và audit theo actor
* deployment profile vẫn bảo thủ quanh single FastAPI process và SQLite local volume; durability, worker isolation và queue/outbox chưa được khóa thành phase riêng
* realtime surface hiện đủ cho shell mỏng nhưng chưa phải streaming contract production-grade với reconnect, cursor continuity và backpressure rõ ràng
* A2A adapter/interoperability vẫn thiên về experimental bridge và adoption thuận tiện, chưa chứng minh compatibility ngoài hệ thống ở mức đủ mạnh để tuyên bố production-grade interop
* release V5 cần được đóng thành product milestone rõ hơn thay vì chỉ dừng ở packaged state

* * *

## 3. Mục tiêu của V6

V6 nên làm rõ 6 hướng:

1. Chốt V5 thành release milestone thật để tạo baseline ổn định cho V6.
2. Mở operator action surface có kiểm soát để người vận hành không chỉ xem mà còn can thiệp được vào flow thật.
3. Bổ sung identity, team roles và audit semantics rõ hơn cho môi trường nhiều người dùng nội bộ.
4. Tăng durability cho runtime và persistence để hệ thống chịu tải vận hành tốt hơn khi dùng thật trong nhóm.
5. Nâng realtime contract từ replay/polling lên streaming rõ nghĩa hơn cho operator experience và integration surface.
6. Chuyển A2A từ mức interop usable sang mức interop có thể verify bằng contract tests và compatibility claims hẹp nhưng đáng tin.

* * *

## 4. Phạm vi của V6

### 4.1 Trong phạm vi

V6 ưu tiên các hướng sau:

1. release closure cho V5:
   * release notes
   * version tag
   * upgrade notes
   * smoke/release verification
2. operator actions:
   * approve/reject/retry/resume/cancel
   * phase transition actions có guardrails
   * action audit trail
   * UI affordances tối thiểu cho các action trên
3. identity và team RBAC mức cơ bản:
   * actor identity
   * session/user attribution
   * role mapping tối thiểu cho operator, reviewer, integration client
   * authorization checks rõ trên operator/public actions
4. durability và runtime isolation tốt hơn:
   * PostgreSQL profile tùy chọn hoặc primary cho team deployment
   * worker split hoặc background execution boundary rõ hơn
   * outbox/inbox hoặc durable queue pattern tối thiểu
   * restart/recovery semantics rõ hơn
5. realtime transport rõ hơn:
   * SSE hoặc WebSocket transport tối thiểu
   * reconnect/cursor resume semantics
   * bounded retention hoặc stream window semantics
6. external interoperability proof:
   * contract tests cho A2A/public surfaces
   * compatibility matrix hẹp nhưng có verify
   * sample clients / integration docs tốt hơn

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V6:

* web product hoàn chỉnh cho end user ngoài operator
* enterprise SSO đầy đủ hoặc identity federation phức tạp
* multi-tenant cloud platform hoàn chỉnh
* distributed coordinator multi-region hoặc cross-host federation phức tạp
* marketplace plugin ecosystem
* thay toàn bộ native coordinator model bằng A2A-first model

* * *

## 5. Nguyên tắc triển khai cho V6

1. Action surface phải đi sau audit và guardrails. Không mở thao tác ghi state từ UI nếu chưa truy vết được ai đã làm gì.

2. Coordinator-first vẫn giữ nguyên. UI, RBAC, streaming hay A2A contract đều phải bám theo state model `session/job/artifact/review/runtime` hiện có thay vì tạo thêm orchestration model thứ hai.

3. Identity phải tối giản nhưng thật. V6 không cần SSO enterprise, nhưng mọi action ghi state cần có actor rõ, role rõ và authorization boundary rõ.

4. Durability trước scale-out. Ưu tiên runtime bền, recover tốt và queue/worker semantics rõ trước khi nói đến distributed platform lớn.

5. Streaming phải kế thừa replay semantics. Realtime transport mới không được phá khả năng replay/debug vốn đã hữu ích ở V5.

6. Compatibility claim phải hẹp nhưng kiểm chứng được. Chỉ tuyên bố các phần A2A/public API mà repo thực sự test được end-to-end.

7. PR nhỏ, rủi ro cô lập. Không gộp release closure, operator actions, RBAC, durable runtime, streaming và interop certification vào cùng một PR lớn.

* * *

## 6. Trình tự triển khai cấp cao

Dự án ở V6 nên đi qua 6 giai đoạn:

G26 → G27 → G28 → G29 → G30 → G31

Trong đó:

* G26 chốt release baseline cho V5
* G27 mở operator actions và audit trail
* G28 thêm identity / team RBAC cơ bản
* G29 nâng durability cho storage/runtime/worker boundary
* G30 nâng realtime transport từ polling/replay sang streaming contract rõ hơn
* G31 khóa interop bằng contract tests, compatibility matrix và external adoption notes

Phụ thuộc:

* G27 phụ thuộc G26 vì action surface nên xuất phát từ một release baseline đã đóng gói và có version rõ
* G28 phụ thuộc G27 vì authorization chỉ có ý nghĩa khi action surface đã xác định rõ các verb ghi state
* G29 phụ thuộc G28 vì worker/action/runtime semantics trong môi trường nhiều người dùng cần actor boundary và auth checks ổn định hơn
* G30 phụ thuộc G29 vì streaming production-ish sẽ phản ánh state/runtime thật và cần dựa trên persistence/delivery semantics đáng tin hơn
* G31 phụ thuộc G30 vì compatibility claims nên bám public contract đã ổn định hơn ở cả action, auth và streaming

* * *

## 7. Kế hoạch chi tiết theo giai đoạn

## G26. Release closure cho V5

Phụ thuộc: G25 / F40  
Mở khóa: G27  
Kết quả: V5 không chỉ “đã code xong” mà trở thành một release milestone rõ, có tag, notes, checklist và baseline để so sánh regression

Bao gồm:

* release notes cho V5
* upgrade notes / migration notes nếu cần
* version bump và release tag strategy
* release verification checklist
* smoke path cho package/release artifact

Không bao gồm:

* action surface mới
* RBAC đầy đủ
* thay đổi runtime lớn

## G27. Operator actions và audit trail

Phụ thuộc: G26  
Mở khóa: G28  
Kết quả: operator shell được nâng thành operator console tối thiểu, có thể thao tác approve/reject/retry/resume/cancel có kiểm soát

Bao gồm:

* action endpoints hoặc command handlers cho operator actions
* UI affordances tối thiểu cho actions
* precondition checks và error mapping rõ
* audit trail theo actor/action/time/reason
* tests cho action flows và rollback/failure edge cases

Không bao gồm:

* team identity đầy đủ
* durable queue lớn
* streaming transport mới

## G28. Identity và team RBAC cơ bản

Phụ thuộc: G27  
Mở khóa: G29  
Kết quả: mọi action ghi state quan trọng đều có actor identity rõ và role checks tối thiểu

Bao gồm:

* actor identity model tối giản
* operator / reviewer / integration client roles
* authorization layer cho operator/public write actions
* audit enrichment theo actor và role
* docs cho access model và trust assumptions

Không bao gồm:

* SSO enterprise
* multi-tenant organization model
* complex policy authoring UI

## G29. Durable runtime và persistence boundary

Phụ thuộc: G28  
Mở khóa: G30  
Kết quả: hệ thống chịu được restart, queueing và background execution tốt hơn trong môi trường nhóm nhỏ nhưng dùng thật

Bao gồm:

* PostgreSQL deployment profile rõ
* migration/backup/restore cho profile mới
* worker split hoặc background execution boundary rõ ràng
* outbox/inbox hoặc durable queue pattern tối thiểu
* recovery tests cho restart/resume/re-delivery

Không bao gồm:

* distributed multi-node scheduler
* autoscaling phức tạp
* cross-region durability

## G30. Realtime streaming contract

Phụ thuộc: G29  
Mở khóa: G31  
Kết quả: operator và client có transport realtime rõ nghĩa hơn polling/replay, nhưng vẫn giữ khả năng replay/debug của V5

Bao gồm:

* SSE hoặc WebSocket transport tối thiểu
* reconnect strategy và cursor resume semantics
* stream envelope rõ cho activity/events
* docs retention/window/backpressure assumptions
* tests cho reconnect, duplicate delivery và cursor continuity

Không bao gồm:

* distributed event bus lớn
* external pub/sub platform bắt buộc
* UI trực quan hóa lớn ngoài nhu cầu vận hành

## G31. Interop certification và adoption rộng hơn

Phụ thuộc: G30  
Mở khóa: phase sau V6  
Kết quả: repo có thể tuyên bố một tập compatibility hẹp nhưng đáng tin cho external clients/agents

Bao gồm:

* contract tests cho public API / public events / A2A bridge surface
* compatibility matrix được hỗ trợ chính thức
* sample clients / integration fixtures
* adoption notes cho reverse proxy, package, auth, streaming và client expectations
* release candidate cho V6

Không bao gồm:

* broad ecosystem guarantees
* third-party hosted SaaS control plane
* universal protocol translation beyond the maintained scope

* * *

## 8. Kết quả mong đợi sau V6

Nếu V6 hoàn tất tốt, hệ thống nên đạt trạng thái sau:

1. Có release baseline rõ cho V5 và V6 thay vì chỉ có trạng thái code nội bộ.
2. Operator có thể xem và thao tác trên flow thật với audit trail đầy đủ hơn.
3. Identity và role đủ rõ để dùng nội bộ theo nhóm mà không mơ hồ ai đang thao tác gì.
4. Runtime/persistence bền hơn cho small-team deployment dùng thật.
5. Realtime surface rõ nghĩa hơn cho operator experience và client integrations.
6. Public/A2A claims hẹp hơn nhưng đáng tin hơn nhờ contract tests và compatibility matrix.

* * *

## 9. Rủi ro chính của V6

1. Mở action surface quá sớm khi audit và authorization chưa ổn sẽ làm operator UI trở thành nguồn gây state corruption.
2. Gộp RBAC, runtime durability và streaming vào một PR lớn sẽ làm chi phí review, rollback và debug tăng mạnh.
3. Đưa PostgreSQL/worker split vào quá sớm mà chưa giữ backward path cho SQLite small-team profile sẽ làm adoption hiện tại bị vỡ.
4. Tuyên bố compatibility/A2A quá rộng hơn phần repo thực sự verify được sẽ làm docs mất độ tin cậy.
5. Streaming mới nếu không bám replay semantics hiện có sẽ làm mất khả năng debug vốn đang là điểm mạnh thực dụng của coordinator.

* * *

## 10. Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. release closure cho V5
2. operator actions + audit trail
3. identity / RBAC cơ bản
4. PostgreSQL + durability boundary
5. realtime streaming contract
6. interop certification / compatibility matrix

* * *

## 11. Cách dùng tài liệu này

Nếu bạn làm một mình:

* đi theo đúng thứ tự G26 → G31
* không mở action surface lớn trước khi audit và authorization ổn
* không mở distributed ambitions khi durable single-team runtime chưa vững

Nếu bạn làm theo sprint:

* có thể gộp G26 + G27 thành một sprint nội bộ
* có thể gộp G30 + G31 nếu contract surface đã ổn
* nhưng vẫn nên giữ merge/review theo PR nhỏ tách biệt

Nếu bạn dùng cùng `docs/planning/archive/IMPLEMENTATION_ORDER_V6.md`:

* `docs/planning/archive/PLAN_V6.md` trả lời câu hỏi: phase V6 nhằm giải quyết vấn đề gì
* `docs/planning/archive/IMPLEMENTATION_ORDER_V6.md` trả lời câu hỏi: nên merge các PR theo thứ tự nào

