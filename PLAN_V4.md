# Kế hoạch phát triển dự án giai đoạn V4: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi **V3 foundation đã hoàn tất tại F31 / PR33**.

Khác với `PLAN_V3.md`:

- `PLAN_V3.md` tập trung mở public collaboration surface, orchestration depth và runtime/operator surface
- `PLAN_V4.md` tập trung **làm cứng hệ thống, đo được hệ thống và chuẩn bị phát hành/triển khai sạch hơn**

Tài liệu này kế thừa và nên đọc cùng:

- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
- `PLAN.md`
- `PLAN_V2.md`
- `PLAN_V3.md`
- `STATUS.md`

---

## 2. Điểm xuất phát của V4

Sau V3, hệ thống đã có:

- A2A public API v1 và public event stream
- session templates, orchestration presets và phase gates
- runtime pools cùng isolated work contexts
- operator dashboard/debug surface
- advanced policy engine và conditional automation
- audit trail, artifact export và review flow rõ hơn

Điểm còn thiếu để đi tiếp:

- hardening cho edge cases, retry boundaries, duplicate actions và failure recovery vẫn chưa được khóa thành một phase riêng
- telemetry hiện mới mạnh ở status/diagnostics aggregate, chưa đủ tốt cho quan sát dài hạn và phân tích theo thời gian
- release checklist, runbook, upgrade notes và operational safety chưa được đóng gói thành release discipline rõ
- deployment surface và external readiness chưa đủ rõ để coi đây là một nền tảng dễ triển khai, dễ vận hành

---

## 3. Mục tiêu của V4

V4 nên làm rõ 5 hướng:

1. Làm cứng các flow quan trọng để lỗi xảy ra có biên rõ, recovery path rõ và không tạo side effect mơ hồ.
2. Bổ sung telemetry và observability đủ sâu để biết hệ thống chậm, fail hoặc tắc ở đâu theo thời gian.
3. Chuẩn hóa release readiness để có thể tạo release candidate, verify và rollback theo checklist rõ.
4. Chuẩn bị deployment/external surface tối thiểu nhưng sạch để hệ thống dễ mang sang môi trường khác.
5. Tạo nền đủ ổn cho operator UI hoặc product UI mỏng ở phase sau mà không phải sửa lại lớp vận hành.

---

## 4. Phạm vi của V4

### 4.1 Trong phạm vi

V4 ưu tiên các hướng sau:

1. hardening cho public API, orchestration, runtime pool, policy automation và CodexBridge boundaries
2. structured logging, correlation IDs, metrics và telemetry read model
3. release readiness:
   - smoke flows
   - migration safety
   - backup/restore tối thiểu
   - release checklist
   - release notes / upgrade notes
4. deployment/external readiness:
   - container hoặc deployment profile tối thiểu
   - startup/readiness contract
   - config profile rõ
   - versioning/release tagging
5. guardrails tối thiểu cho operator/public surface:
   - rate limiting hoặc quota guardrails nhẹ
   - auth/config hooks tối thiểu nếu cần
   - safer defaults cho môi trường ngoài local

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V4:

- web product hoàn chỉnh cho end user
- operator UI lớn vượt quá nhu cầu vận hành tối thiểu
- auth production-grade đầy đủ hoặc SSO enterprise
- multi-tenant cloud platform hoàn chỉnh
- distributed coordinator hoặc cross-host federation phức tạp
- fork sâu vào Codex runtime

---

## 5. Nguyên tắc triển khai cho V4

1. **Ổn định trước khi mở UI.**
   Nếu nền vận hành chưa đủ cứng và chưa đo được, UI chỉ che giấu vấn đề chứ không giải quyết nó.

2. **Coordinator-first vẫn giữ nguyên.**
   Hardening, telemetry và deployment không được làm lệch kiến trúc điều phối trung tâm hiện có.

3. **Telemetry phải dựa trên state thật.**
   Metrics, logs và dashboards phải phản ánh `session/job/artifact/phase/runtime` thật thay vì chỉ scrape log thô.

4. **Public contract phải giữ ổn định.**
   Mọi thay đổi hardening trên public API phải ưu tiên compatibility, error mapping rõ và có regression tests.

5. **Release phải lặp lại được.**
   Một release candidate chỉ có giá trị nếu có checklist, smoke path và rollback path đủ rõ cho người khác chạy lại.

6. **Ưu tiên an toàn vận hành hơn mở tính năng mới.**
   V4 không nên bị trôi thành một phase feature expansion trá hình.

7. **PR nhỏ, rủi ro cô lập.**
   Không gộp hardening sâu, telemetry, release prep và deployment packaging vào cùng một PR lớn.

---

## 6. Trình tự triển khai cấp cao

Dự án ở V4 nên đi qua 4 giai đoạn:

**G17 → G18 → G19 → G20**

Trong đó:

- **G17** làm cứng reliability và recovery
- **G18** mở telemetry/observability theo thời gian
- **G19** khóa release readiness và operational safety
- **G20** chuẩn hóa deployment/external readiness

Phụ thuộc:

- G18 phụ thuộc G17 vì telemetry trên flow chưa ổn định sẽ cho tín hiệu nhiễu và khó tin
- G19 phụ thuộc G18 vì release checklist cần có dữ liệu vận hành và diagnostics đáng tin
- G20 phụ thuộc G19 vì deployment surface nên được đóng gói trên một release candidate đủ ổn định

---

## 7. Kế hoạch chi tiết theo giai đoạn

## G17. Hardening và reliability
**Phụ thuộc:** G16 / F31  
**Mở khóa:** G18  
**Kết quả:** các flow quan trọng fail có kiểm soát, recovery path rõ và side effect được khóa tốt hơn

### Công việc
1. Rà soát validation và error mapping cho:
   - public A2A API
   - event stream replay/cursor
   - template instantiation
   - orchestration actions
   - policy/operator actions
2. Thêm guard cho duplicate actions và idempotency tối thiểu ở các flow dễ bị retry:
   - create task
   - interrupt/requeue/retry
   - review decision
   - phase transition
3. Làm rõ timeout, cleanup và fallback boundaries quanh CodexBridge, runtime pools và work contexts
4. Kiểm tra migration safety, startup checks và backward-compatible defaults
5. Mở rộng integration tests cho failure, recovery và edge-case flows

### Tiêu chí xong
- lỗi trả ra có loại rõ và nhất quán hơn
- retry/replay không tạo duplicate state khó giải thích
- runtime hoặc bridge failure có đường recovery/fallback nhìn thấy được
- regression tests bao phủ các flow có rủi ro cao

---

## G18. Telemetry và observability
**Phụ thuộc:** G17  
**Mở khóa:** G19  
**Kết quả:** operator biết cái gì đang chậm, fail hoặc tắc theo thời gian thay vì chỉ thấy aggregate health

### Công việc
1. Chuẩn hóa structured logging với correlation IDs cho:
   - session
   - agent
   - job
   - phase
   - review
   - public task
   - runtime assignment
2. Thêm metrics hoặc telemetry counters cho:
   - queue depth
   - job latency
   - phase duration
   - review bottlenecks
   - runtime pool health
   - CodexBridge error rates
   - public task/event throughput
3. Tạo telemetry read model hoặc diagnostics surfaces cho recent failures, latency windows và throughput windows
4. Tách rõ aggregate health với live/recent telemetry để `system/status` không phải gánh toàn bộ trách nhiệm quan sát
5. Viết docs cho semantics của log/metric/event và tests ở mức service hoặc integration

### Tiêu chí xong
- có thể trả lời “chậm ở đâu”, “fail ở đâu” và “phase nào đang tắc” bằng telemetry surface rõ
- correlation IDs đủ để nối từ API request sang job/phase/runtime liên quan
- CodexBridge health không còn chỉ là snapshot aggregate

---

## G19. Release readiness và operational safety
**Phụ thuộc:** G18  
**Mở khóa:** G20  
**Kết quả:** có thể tạo release candidate, kiểm chứng và rollback bằng quy trình rõ thay vì thao tác ngẫu hứng

### Công việc
1. Chốt release checklist tối thiểu:
   - `pytest`
   - lint
   - smoke test
   - migration verification
   - seed/reset verification
2. Viết runbook cho:
   - local/dev startup
   - prod-like startup tối thiểu
   - incident triage
   - backup/restore SQLite
   - recovery sau runtime/CodexBridge failure
3. Chuẩn hóa config profiles, env var docs và safe defaults theo môi trường
4. Cập nhật release notes, upgrade notes, docs vận hành và README/STATUS/API docs cho nhất quán
5. Thêm acceptance suite hoặc release gate tối thiểu cho release candidate

### Tiêu chí xong
- có thể dựng một release candidate theo checklist lặp lại được
- người khác có thể vận hành hoặc debug theo runbook mà không cần hỏi tác giả
- backup/restore và migration path được mô tả rõ ở mức tối thiểu chấp nhận được

---

## G20. Deployment surface và external readiness
**Phụ thuộc:** G19  
**Mở khóa:** roadmap xa hơn  
**Kết quả:** hệ thống có surface triển khai sạch hơn, đủ an toàn để đưa vào môi trường ngoài local và làm nền cho UI phase sau

### Công việc
1. Chuẩn hóa deployment profile tối thiểu:
   - container image hoặc runtime packaging
   - startup/readiness checks
   - strategy áp migration khi boot
2. Thêm CI quality gates hoặc scripts tương ứng cho test/lint/smoke/docs consistency
3. Bổ sung guardrails tối thiểu cho public/operator surface:
   - config-based access boundaries
   - rate limiting hoặc quota guardrails nhẹ
   - production-safe defaults
4. Chốt versioning/release tagging và compatibility notes cho API, migrations và docs
5. Viết docs về topology triển khai tối thiểu và kỳ vọng tích hợp ngoài hệ thống

### Tiêu chí xong
- có ít nhất một topology triển khai được hỗ trợ rõ ràng
- môi trường ngoài local có guardrails cơ bản thay vì chạy với mặc định quá rộng
- dự án sẵn sàng hơn cho operator UI mỏng hoặc mở rộng adoption mà không phải làm lại lớp vận hành

---

## 8. Backlog V4 theo feature

Backlog cụ thể cho V4 nên đi theo chuỗi:

**F32 → F33 → F34 → F35**

Trong đó:

- F32: hardening và reliability
- F33: telemetry và observability
- F34: release readiness và operational safety
- F35: deployment surface và external readiness

Chi tiết nên được chốt tiếp trong:

- `IMPLEMENTATION_TASKS_V4.md`
- `IMPLEMENTATION_ORDER_V4.md`

---

## 9. Các mốc bàn giao quan trọng

### M17 — Reliable core
Đạt sau G17.

Bạn có:

- failure boundaries rõ hơn
- retry/recovery ít gây side effect mơ hồ hơn
- regression coverage tốt hơn cho flow quan trọng

### M18 — Observable core
Đạt sau G18.

Bạn có:

- structured telemetry
- diagnostics theo thời gian
- correlation IDs đủ để truy vết end-to-end

### M19 — Release candidate ready
Đạt sau G19.

Bạn có:

- release checklist rõ
- runbook vận hành cơ bản
- docs/release notes đồng bộ hơn

### M20 — Deployable coordinator surface
Đạt sau G20.

Bạn có:

- deployment profile tối thiểu
- guardrails cơ bản cho môi trường ngoài local
- nền đủ ổn để bước sang UI mỏng hoặc adoption rộng hơn

---

## 10. Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. hardening và reliability
2. telemetry và observability
3. release readiness
4. operational safety / backup / restore
5. deployment surface tối thiểu
6. guardrails cho public/operator surface

---

## 11. Kết luận

V4 không nên nhảy thẳng sang UI hoàn chỉnh.

V4 nên khóa bốn thứ trước:

1. **flow quan trọng fail có kiểm soát**
2. **telemetry đủ để biết hệ thống đang xảy ra chuyện gì**
3. **release có checklist, runbook và rollback path rõ**
4. **deployment surface đủ sạch để đi ra ngoài local**

Khi bốn phần này ổn, dự án sẽ có nền chắc hơn để làm operator UI mỏng, product UI bước đầu hoặc deployment rộng hơn mà không phải quay lại sửa lớp vận hành cốt lõi.
