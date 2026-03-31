# Kế hoạch phát triển dự án giai đoạn V3: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi **V2 foundation đã hoàn tất tại F24 / PR26**.

Khác với `PLAN_V2.md`:

- `PLAN_V2.md` tập trung làm dày nền coordinator để vận hành tốt hơn
- `PLAN_V3.md` tập trung mở **public collaboration surface** và **orchestration depth** trên nền đã có

Tài liệu này kế thừa và nên đọc cùng:

- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
- `PLAN.md`
- `PLAN_V2.md`
- `STATUS.md`

---

## 2. Điểm xuất phát của V3

Sau V2, hệ thống đã có:

- system status, diagnostics và debug surface
- session channels, participant roles/policies và rules cơ bản
- advanced jobs với create/retry/resume/offline queue
- artifact metadata và transcript export
- review mode cùng structured relay templates
- phase presets nhẹ
- experimental A2A adapter bridge tách khỏi core model

Điểm còn thiếu để đi tiếp:

- public A2A API còn ở mức bridge thử nghiệm
- event streaming cho client ngoài còn chưa có contract rõ
- orchestration vẫn chủ yếu theo flow nội bộ, chưa đủ mạnh cho template/session automation
- runtime isolation và operator surface lớn hơn vẫn chưa được đóng gói thành module V3

---

## 3. Mục tiêu của V3

V3 nên làm rõ 6 hướng:

1. Biến experimental adapter thành **A2A public API v1** có contract rõ.
2. Thêm **public subscribe/push model** để client ngoài theo dõi task/status/artifact mà không polling thô.
3. Thêm **session templates và orchestration presets** để tạo session có cấu trúc lặp lại được.
4. Nâng cấp **review/orchestration** với phase gates, approval gates và handoff có điều kiện.
5. Tạo **runtime pools hoặc isolated work contexts** cho agent khi workload tăng.
6. Mở rộng **operator surface và policy engine** để điều phối an toàn hơn ở quy mô lớn hơn.

---

## 4. Phạm vi của V3

### 4.1 Trong phạm vi

V3 ưu tiên các hướng sau:

1. A2A public task API versioned
2. public event stream cho task/status/artifact
3. session templates và preset instantiation
4. advanced orchestration:
   - gated phase transitions
   - review-required / approval-required transitions
   - auto-create handoff jobs
5. runtime pool registry và isolated work context theo agent
6. dashboard-ready operator APIs
7. policy engine nâng cao:
   - conditional auto-approve
   - policy scopes theo session/phase/template
   - escalation rõ hơn

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V3:

- auth production-grade đầy đủ
- multi-tenant cloud deployment hoàn chỉnh
- cross-host federation hoặc distributed coordinator phức tạp
- fork sâu vào Codex runtime
- web product hoàn chỉnh vượt quá nhu cầu operator/debug

---

## 5. Nguyên tắc triển khai cho V3

1. **Coordinator-first vẫn giữ nguyên.**
   Public API không được đẩy orchestration xuống agent runtime.

2. **Internal model vẫn là nguồn sự thật.**
   `session/job/artifact/phase` tiếp tục là canonical model; A2A chỉ là public mapping layer.

3. **Public contract phải versioned.**
   Nếu mở route public, payload và status mapping phải có version và docs rõ.

4. **Event-first, không polling thô.**
   Public clients nên theo dõi bằng subscription/stream có cursor hoặc replay tối thiểu.

5. **Runtime isolation phải explicit.**
   Nếu thêm worktree/pool, assignment và lifecycle phải được ghi DB rõ ràng.

6. **Policy automation đứng trên repository + services hiện có.**
   Không viết lại core rules engine từ đầu nếu có thể mở rộng theo lớp.

7. **PR nhỏ, demo rõ.**
   Không gộp public API, runtime isolation, dashboard và policy engine vào cùng một PR lớn.

---

## 6. Trình tự triển khai cấp cao

Dự án ở V3 nên đi qua 4 giai đoạn:

**G13 → G14 → G15 → G16**

Trong đó:

- **G13** mở public protocol surface
- **G14** làm dày orchestration bằng templates và phase gates
- **G15** thêm execution isolation cho runtime
- **G16** mở rộng operator control và policy automation

Phụ thuộc:

- G14 phụ thuộc G13 vì orchestration ngoài core cần public task/event contract ổn định
- G15 phụ thuộc G14 vì runtime isolation cần biết agent đang chạy flow nào
- G16 phụ thuộc G15 vì dashboard/policy cần phản ánh runtime và orchestration state thật

---

## 7. Kế hoạch chi tiết theo giai đoạn

## G13. A2A public surface và event subscriptions
**Phụ thuộc:** G12 / F24  
**Mở khóa:** G14  
**Kết quả:** client ngoài có thể tạo, đọc và theo dõi task qua contract public rõ ràng

### Công việc
1. Chuẩn hóa A2A public task model từ adapter hiện có
2. Tạo public routes cho:
   - create task
   - get task
   - list task
   - list task artifacts/events tối thiểu
3. Tạo subscribe/push model với stream hoặc subscription cursor rõ ràng
4. Chuẩn hóa public status mapping từ internal job/phase/review state
5. Viết docs contract và integration tests

### Tiêu chí xong
- external client tạo được task công khai mà không chạm internal API
- external client theo dõi được trạng thái qua stream/subscription rõ
- mapping job/task/artifact không làm bẩn core coordinator model

---

## G14. Session templates và orchestration nâng cao
**Phụ thuộc:** G13  
**Mở khóa:** G15  
**Kết quả:** session có thể khởi tạo từ template và chạy qua flow phase/review nhất quán hơn

### Công việc
1. Tạo session templates:
   - planning-heavy
   - implementation-review
   - research-review
   - hotfix-triage
2. Cho template định nghĩa:
   - default channels
   - participant roles
   - phase order
   - rule presets
3. Thêm gated phase transitions:
   - review-required
   - approval-required
   - revise-on-reject
4. Tạo orchestration service cho handoff jobs và decision artifacts
5. Viết integration tests cho template-driven flow

### Tiêu chí xong
- tạo session từ template được
- phase transition chịu tác động bởi gate/policy rõ
- builder-reviewer-revise flow chạy được mà không cần điều phối tay quá nhiều

---

## G15. Runtime pools và isolated work contexts
**Phụ thuộc:** G14  
**Mở khóa:** G16  
**Kết quả:** coordinator có thể gán execution vào pool/context rõ hơn khi số agent hoặc workload tăng

### Công việc
1. Tạo runtime pool registry
2. Cho agent/session/job gắn với runtime capability hoặc pool preference
3. Thêm isolated work context:
   - repo binding
   - worktree/path binding
   - lifecycle cleanup policy
4. Mở rộng diagnostics cho runtime pool utilization
5. Viết tests cho assignment, recovery và fallback

### Tiêu chí xong
- coordinator chọn runtime/pool theo policy hoặc capability
- agent có context làm việc rõ hơn, giảm đè nhau trên cùng workspace khi cần
- runtime failure/recovery được nhìn thấy từ operator surface

---

## G16. Operator dashboard surface và policy automation
**Phụ thuộc:** G15  
**Mở khóa:** roadmap xa hơn  
**Kết quả:** operator có bề mặt quan sát/điều phối mạnh hơn và policy tự động hóa ở mức an toàn

### Công việc
1. Mở rộng dashboard-ready APIs:
   - queue heat
   - phase distribution
   - review bottlenecks
   - runtime pool health
   - public task throughput
2. Tạo policy engine nâng cao:
   - conditional auto-approve
   - escalation theo phase/template
   - policy scopes theo session/template/agent role
3. Bổ sung audit trail tốt hơn cho policy decisions
4. Nếu cần, thêm operator actions có guardrails rõ:
   - requeue
   - force phase change
   - pause automation
5. Viết integration tests cho policy automation và operator actions

### Tiêu chí xong
- operator biết session/job nào đang tắc theo dashboard surface
- policy decisions có thể giải thích và audit được
- automation không phá nguyên tắc coordinator-first

---

## 8. Backlog V3 theo feature

Backlog cụ thể cho V3 nên đi theo chuỗi:

**F25 → F26 → F27 → F28 → F29 → F30 → F31**

Trong đó:

- F25: A2A public API v1
- F26: public subscribe/push event model
- F27: session templates và orchestration presets
- F28: advanced review orchestration và phase gates
- F29: runtime pools và isolated work contexts
- F30: operator dashboard/debug expansion
- F31: advanced policy engine và conditional automation

Chi tiết nằm ở:

- `IMPLEMENTATION_TASKS_V3.md`
- `IMPLEMENTATION_ORDER_V3.md`

---

## 9. Các mốc bàn giao quan trọng

### M13 — Public protocol ready
Đạt sau G13.

Bạn có:

- A2A public task API v1
- event subscribe/push model rõ
- mapping public/internal ổn định hơn

### M14 — Template-driven orchestration
Đạt sau G14.

Bạn có:

- session templates
- phase gates
- review/revise flow có automation rõ hơn

### M15 — Isolated execution surface
Đạt sau G15.

Bạn có:

- runtime pools
- isolated work contexts
- diagnostics tốt hơn cho execution assignment

### M16 — Operator control v2
Đạt sau G16.

Bạn có:

- dashboard-ready operator APIs
- policy automation nâng cao
- audit trail tốt hơn cho orchestration decisions

---

## 10. Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. A2A public API
2. public event subscriptions
3. session templates
4. advanced orchestration/review gates
5. runtime pools và isolated work contexts
6. operator dashboard expansion
7. advanced policy automation

---

## 11. Kết luận

V3 không nên nhảy thẳng sang platform hóa quá sớm.

V3 nên khóa bốn thứ trước:

1. **public contract rõ**
2. **event model rõ**
3. **orchestration đủ mạnh cho template và review gates**
4. **runtime/operator control đủ sạch để scale tiếp**

Khi bốn phần này ổn, dự án sẽ có đường đi sạch hơn sang public collaboration platform, runtime scaling và policy automation sâu hơn mà không phải viết lại lõi coordinator.
