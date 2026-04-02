# PLAN_V2.md

## 1. Mục tiêu của tài liệu

Tài liệu này mở rộng roadmap sau khi **MVP đã hoàn thành tại F16 / PR18**.

Khác với `docs/planning/archive/PLAN.md`:

- `docs/planning/archive/PLAN.md` chốt phạm vi từ F01 đến F16 để bàn giao MVP
- `docs/planning/archive/PLAN_V2.md` chốt hướng phát triển **post-MVP / V2**
- trọng tâm chuyển từ “chạy được và demo được” sang “dùng được lâu hơn, quan sát được tốt hơn, cộng tác sâu hơn”

Tài liệu này kế thừa và phải đọc cùng:

- `docs/reference/PRD.md`
- `docs/reference/ARCHITECTURE.md`
- `docs/reference/API.md`
- `docs/reference/DB_SCHEMA.md`
- `docs/planning/archive/PLAN.md`
- `docs/planning/STATUS.md`

---

## 2. Mục tiêu của V2

Sau MVP, hệ thống đã có:

- session chung
- mention routing
- relay engine
- command control
- presence, recovery, loop guard
- artifacts, approvals, streaming
- bề mặt A2A-ready tối thiểu

V2 cần làm cho coordinator trở thành một hệ thống **vận hành được tốt hơn và điều phối cộng tác rõ hơn**, cụ thể:

1. Có **operator surface** tốt hơn để biết hệ thống đang khỏe hay đang tắc ở đâu
2. Có **cấu trúc collaboration sâu hơn** thay vì chỉ một session phẳng
3. Có **job model giàu hơn** để retry, resume, queue và review dễ hơn
4. Có **artifact và transcript export** đủ tốt cho debug, review và handoff
5. Có **review workflow** rõ hơn giữa planner, builder, reviewer
6. Có **phase/preset** nhẹ để chuẩn bị cho structured collaboration
7. Chuẩn bị **adapter bridge sang A2A** mà không làm lẫn Coordinator API với public API

---

## 3. Phạm vi của V2

### 3.1 Trong phạm vi

V2 ưu tiên các hướng sau:

1. `system/status`, diagnostics và debug surface
2. channels hoặc views cho session
3. role/policy/rule cơ bản ở mức coordinator
4. advanced jobs:
   - direct job creation
   - retry
   - resume
   - normalized job inputs
   - offline queue tối thiểu
5. artifact improvements:
   - transcript export
   - file bundle tốt hơn
   - revisit/review summary
6. review mode và relay templates
7. phase presets nhẹ
8. experimental A2A adapter bridge ở mức adapter riêng, có thể đặt sau feature flag

### 3.2 Ngoài phạm vi

Các phần sau **chưa phải trọng tâm của V2**:

- auth production-grade đầy đủ
- multi-tenant
- cloud deployment hoàn chỉnh
- multi-runtime pool phức tạp
- repo/worktree riêng cho mỗi agent
- A2A public API production-ready
- dashboard web lớn

---

## 4. Nguyên tắc triển khai cho V2

1. **Coordinator-first vẫn giữ nguyên.**
   Không đẩy orchestration xuống từng agent runtime.

2. **Codex vẫn là execution engine.**
   Không fork Codex và không trộn primitive của Codex trực tiếp vào API public.

3. **Adapter phải ở ngoài lõi.**
   Nếu thêm A2A, đó phải là adapter layer riêng, không thay thế session/job model nội bộ.

4. **State và event vẫn là nguồn sự thật.**
   Mọi tính năng mới phải ghi được DB và event/audit trail rõ ràng.

5. **Tăng độ phức tạp theo lớp.**
   Quan sát vận hành trước, rồi cộng tác sâu hơn, rồi mới mở adapter/public surface.

6. **PR nhỏ, demo rõ.**
   Không gộp channels, rules, review mode, phase presets và A2A adapter vào cùng một PR lớn.

7. **Không viết lại kiến trúc.**
   V2 mở rộng bằng các module, table và route mới theo kiến trúc hiện tại.

---

## 5. Trình tự triển khai cấp cao

Dự án sau MVP sẽ đi qua 4 giai đoạn:

**G09 → G10 → G11 → G12**

Trong đó:

- **G09** tăng quan sát và khả năng vận hành
- **G10** thêm cấu trúc collaboration cho session
- **G11** làm dày job/artifact/review flow
- **G12** thêm phase presets và bridge sang adapter/public surface

Phụ thuộc:

- G10 phụ thuộc G09 vì channels, roles và rules cần dựa trên surface quan sát/debug rõ hơn
- G11 phụ thuộc G10 vì review flow và advanced jobs cần cấu trúc collaboration rõ
- G12 phụ thuộc G11 vì phase và adapter bridge cần job/artifact/review model ổn định hơn

---

## 6. Kế hoạch chi tiết theo giai đoạn

## G09. Operator visibility và diagnostics
**Phụ thuộc:** G08 / F16  
**Mở khóa:** G10  
**Kết quả:** coordinator có surface quan sát đủ tốt để vận hành, debug và demo sau MVP

### Công việc
1. Hoàn thiện `GET /api/v1/system/status`
2. Thêm debug aggregates cho:
   - active sessions
   - active agents
   - queued/running jobs
   - pending approvals
   - recent artifacts
3. Chuẩn hóa structured logging cho session/agent/job/turn
4. Bổ sung session/job diagnostics APIs hoặc internal debug surface
5. Viết test cho luồng status/diagnostics

### Tiêu chí xong
- có thể biết coordinator, DB, CodexBridge và queue đang khỏe hay không
- có thể trả lời “job nào đang tắc” mà không cần đọc log thô

---

## G10. Collaboration structure: channels, roles, rules
**Phụ thuộc:** G09  
**Mở khóa:** G11  
**Kết quả:** session không còn là một luồng chat phẳng duy nhất; policy collaboration rõ hơn

### Công việc
1. Thêm channel hoặc view model cho session:
   - `general`
   - `planning`
   - `review`
   - `debug`
2. Bổ sung role model ở mức participant/session
3. Bổ sung permission matrix rõ hơn cho:
   - lead
   - builder
   - reviewer
   - planner
   - researcher
4. Thêm rules cơ bản:
   - manual activation
   - policy proposal
   - auto-relay guardrails
5. Viết test cho routing theo channel/role/rule

### Tiêu chí xong
- session lớn vẫn đọc được
- relay không phụ thuộc hoàn toàn vào text chat phẳng
- rule có thể được activate/deactivate mà không sửa code tay

---

## G11. Advanced jobs, artifacts và review workflows
**Phụ thuộc:** G10  
**Mở khóa:** G12  
**Kết quả:** job lifecycle, artifact model và review flow đủ mạnh cho collaboration thực tế hơn

### Công việc
1. Nâng cấp job model:
   - `GET /api/v1/jobs`
   - `POST /api/v1/jobs`
   - retry
   - resume
   - normalized `job_inputs`
2. Thêm offline queue tối thiểu cho agent offline
3. Nâng artifact model:
   - transcript export
   - file bundle/export metadata tốt hơn
   - review/revisit summary
4. Thêm review mode:
   - builder → reviewer handoff rõ ràng
   - review result artifact/message rõ loại
5. Viết integration tests cho advanced job + review flow

### Tiêu chí xong
- có thể tạo job trực tiếp ngoài message parser
- một job failed hoặc paused có thể được retry/resume theo contract rõ
- reviewer có luồng làm việc riêng, không chỉ là chat tự do

---

## G12. Phase presets và adapter bridge
**Phụ thuộc:** G11  
**Mở khóa:** kế hoạch V3  
**Kết quả:** coordinator có structured collaboration nhẹ và có adapter bridge rõ ràng cho phase sau

### Công việc
1. Thêm `phases` và phase presets:
   - planning
   - implementation
   - review
   - revise
   - finalize
2. Bổ sung phase-aware relay templates
3. Tạo experimental `A2AAdapter` layer riêng:
   - không thay Coordinator API
   - map `job` sang `task`
   - map stream/artifact/status rõ hơn
4. Nếu cần, thêm `a2a_tasks` mapping table
5. Viết docs migration path từ V2 sang V3

### Tiêu chí xong
- session có preset collaboration nhẹ
- adapter bridge tồn tại như một lớp ngoài, không làm bẩn core model
- có đường đi rõ cho A2A public API ở V3

---

## 7. Backlog V2 theo feature

Backlog cụ thể cho V2 sẽ đi theo chuỗi:

**F17 → F18 → F19 → F20 → F21 → F22 → F23 → F24**

Trong đó:

- F17: system status, diagnostics, debug surface
- F18: channels/views
- F19: roles, permissions, participant policy
- F20: advanced jobs và offline queue
- F21: rules engine cơ bản
- F22: artifact improvements và transcript export
- F23: review mode và structured relay templates
- F24: phase presets và experimental A2A adapter bridge

Chi tiết nằm ở:

- `docs/planning/archive/IMPLEMENTATION_TASKS_V2.md`
- `docs/planning/archive/IMPLEMENTATION_ORDER_V2.md`

---

## 8. Các mốc bàn giao quan trọng

### M9 — Operator-ready surface
Đạt sau G09.

Bạn có:

- `system/status`
- debug view
- queued/pending visibility
- log đủ để truy vết job và relay chain

### M10 — Structured collaboration v1
Đạt sau G10.

Bạn có:

- channels/views
- roles rõ hơn
- rule activation cơ bản

### M11 — Reviewable execution flows
Đạt sau G11.

Bạn có:

- advanced jobs
- offline queue tối thiểu
- transcript export
- review mode

### M12 — V2 foundation complete
Đạt sau G12.

Bạn có:

- phase presets nhẹ
- adapter bridge riêng cho A2A/public surface
- roadmap V3 rõ hơn mà không phải viết lại lõi

---

## 9. Kế hoạch sau V2

### V3

Sau khi V2 ổn, phase kế tiếp nên tập trung vào:

- A2A public API hoàn chỉnh
- public subscribe/push model rõ hơn
- review/orchestration nâng cao
- nhiều runtime pool hoặc repo/worktree riêng theo agent
- dashboard quan sát/debug lớn hơn
- policy engine nâng cao

### Không nên làm sớm hơn

Các phần sau nên để lại cho V3 hoặc xa hơn:

- auth production-grade đầy đủ
- deployment cloud nhiều tenant
- cross-host runtime coordination
- fork sâu vào Codex runtime

---

## 10. Cách làm việc được khuyến nghị cho V2

### 10.1 Cỡ thay đổi cho mỗi PR

Mỗi PR nên chỉ làm một trong các nhóm sau:

- một migration group
- một route group
- một service coordination mới
- một policy/rule slice
- một export/debug surface
- một integration flow

### 10.2 Quy tắc “xong” cho từng task

Một task V2 được xem là xong khi có đủ:

1. code chạy được
2. test liên quan pass
3. log/error handling đủ để debug
4. tài liệu route hoặc hành vi được cập nhật
5. có ít nhất một cách demo tay rõ ràng

### 10.3 Thứ tự ưu tiên nếu phải cắt phạm vi

Nếu thiếu thời gian, hãy giữ thứ tự này:

1. observability và status surface
2. advanced jobs
3. artifact/export
4. review mode
5. roles/rules
6. channels/views
7. phase presets
8. experimental A2A adapter

---

## 11. Kết luận

V2 không nên nhảy thẳng sang public A2A hoàn chỉnh.

V2 nên khóa ba thứ trước:

1. **biết hệ thống đang xảy ra chuyện gì**
2. **điều phối collaboration rõ hơn trong session**
3. **tạo job/review/artifact đủ mạnh cho dùng thật**

Khi ba phần này ổn, việc mở adapter/public API ở V3 sẽ sạch hơn, ít phải sửa lại lõi hơn và đúng với hướng **coordinator-first, CodexBridge-backed, adapter-outside-core** của toàn bộ dự án.
