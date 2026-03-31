# IMPLEMENTATION_ORDER_V2.md

# Thứ tự triển khai theo PR sau MVP: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `IMPLEMENTATION_TASKS_V2.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho phase sau MVP.

Khác với `IMPLEMENTATION_ORDER.md`:

- `IMPLEMENTATION_ORDER.md` chốt PR01-PR18 để hoàn thành MVP
- `IMPLEMENTATION_ORDER_V2.md` chốt **PR19-PR26** cho V2

Mục tiêu của tài liệu:

- cho biết sau MVP thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review dễ
- đảm bảo PR sau dựa trên PR trước
- tránh gộp observability, channels, jobs, rules, review mode và adapter bridge vào cùng một PR lớn

---

## 2. Nguyên tắc chia PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải để hệ thống ở trạng thái dùng được tốt hơn trước.**
3. **PR thêm hành vi mới thì phải thêm test tối thiểu.**
4. **PR sau chỉ bắt đầu khi PR trước đã merge hoặc đã ổn định cục bộ.**
5. **Không gộp phase presets và experimental A2A adapter với các PR nền như jobs hoặc channels.**
6. **Ưu tiên dọc theo luồng dùng thật:** biết hệ thống khỏe không → tổ chức session tốt hơn → giao việc rõ hơn → review rõ hơn → mới mở adapter bridge.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR19 → PR20 → PR21 → PR22 → PR23 → PR24 → PR25 → PR26**

Không có PR nào bị cô lập:

- PR19 mở đường cho PR20
- PR26 phụ thuộc PR25
- mỗi PR ở giữa vừa nhận đầu vào từ PR trước, vừa mở khóa PR sau

---

## 4. Danh sách PR theo thứ tự triển khai

## PR19. System status, diagnostics và debug surface
**Phụ thuộc:** PR18  
**Dựa trên tasks:** F17  
**Mục tiêu:** có surface quan sát đủ tốt để vận hành coordinator sau MVP

### Bao gồm
- hoàn thiện `GET /api/v1/system/status`
- thêm queued/running/pending aggregates
- structured logging fields cho session/agent/job/turn
- tests cho status và diagnostics

### Không bao gồm
- channels
- role matrix mới
- review mode

### Điều kiện merge
- operator có thể biết DB và CodexBridge đang ổn hay không
- thấy được queued jobs và pending approvals
- route tests pass

### Demo sau PR
- gọi `system/status` và nhìn thấy coordinator health cùng các đếm chính

---

## PR20. Channels hoặc views cho session
**Phụ thuộc:** PR19  
**Dựa trên tasks:** F18  
**Mục tiêu:** session có cấu trúc conversation rõ hơn thay vì một luồng chat phẳng

### Bao gồm
- migration cho channel/view model
- repository và service cho channels/views
- channel mặc định `general`, `planning`, `review`, `debug`
- API list/create channels
- tests cho message filtering theo channel/view

### Không bao gồm
- role matrix đầy đủ
- rules engine

### Điều kiện merge
- session mới có channel/view mặc định
- có thể lọc message theo channel/view
- API và repository tests pass

### Demo sau PR
- tạo session, liệt kê channels và gửi message vào `review` hoặc `planning`

---

## PR21. Roles, permissions và participant policy
**Phụ thuộc:** PR20  
**Dựa trên tasks:** F19  
**Mục tiêu:** hành vi của participant rõ hơn ở mức session

### Bao gồm
- role model cho participant
- policy matrix cho relay, interrupt, compact, direct job creation
- API cập nhật participant role/policy
- unit tests cho lead/non-lead và các role chính

### Không bao gồm
- offline queue
- rules engine activation

### Điều kiện merge
- participant role có hiệu lực trong permission checks
- lead/non-lead và reviewer/builder có ranh giới rõ hơn
- permission tests pass

### Demo sau PR
- đổi role participant trong session và quan sát command/relay được cho phép hoặc bị chặn đúng

---

## PR22. Advanced jobs và offline queue tối thiểu
**Phụ thuộc:** PR21  
**Dựa trên tasks:** F20  
**Mục tiêu:** job trở thành đơn vị điều phối mạnh hơn, không chỉ phát sinh từ mention

### Bao gồm
- `GET /api/v1/jobs`
- `POST /api/v1/jobs`
- retry/resume job
- normalized `job_inputs`
- offline queue tối thiểu cho agent offline
- integration tests cho create/retry/resume/queue

### Không bao gồm
- rules engine
- transcript export

### Điều kiện merge
- có thể tạo job trực tiếp qua API
- job failed hoặc paused có thể retry/resume
- agent offline có queue tối thiểu

### Demo sau PR
- tạo job trực tiếp cho builder và resume lại sau khi agent online lại

---

## PR23. Rules engine cơ bản và manual activation
**Phụ thuộc:** PR22  
**Dựa trên tasks:** F21  
**Mục tiêu:** policy collaboration có thể bật/tắt mà không phải đổi code cho từng session

### Bao gồm
- migration cho `rules`
- rules repository
- rule engine cơ bản
- API create/list/activate/deactivate
- tests cho rule activation và evaluation cơ bản

### Không bao gồm
- transcript export
- review mode

### Điều kiện merge
- ít nhất một flow relay hoặc review chịu ảnh hưởng bởi rule
- rule có thể activate/deactivate qua API
- tests pass

### Demo sau PR
- bật một rule review-required và thấy flow job thay đổi đúng

---

## PR24. Artifact improvements và transcript export
**Phụ thuộc:** PR23  
**Dựa trên tasks:** F22  
**Mục tiêu:** output session/job đủ tốt cho debug, review và handoff

### Bao gồm
- artifact metadata mở rộng
- transcript export service
- session artifact listing tốt hơn
- nếu cần, export bundle hoặc attachment support tối thiểu
- tests cho export và artifact metadata

### Không bao gồm
- review orchestration đầy đủ
- phases

### Điều kiện merge
- tạo được transcript export rõ ràng
- artifact metadata đủ để download/debug tốt hơn
- tests pass

### Demo sau PR
- export transcript của một session và xem artifact bundle sinh ra

---

## PR25. Review mode và structured relay templates
**Phụ thuộc:** PR24  
**Dựa trên tasks:** F23  
**Mục tiêu:** builder-reviewer collaboration có flow rõ và lặp lại được

### Bao gồm
- review mode service
- relay templates planner → builder → reviewer → builder revise
- review summary hoặc decision artifacts
- integration tests cho review flow

### Không bao gồm
- phase presets
- A2A adapter bridge

### Điều kiện merge
- builder-reviewer flow chạy được end-to-end
- review output có artifact/message có cấu trúc
- integration tests pass

### Demo sau PR
- builder tạo patch, reviewer trả decision, builder nhận revise instruction qua flow chuẩn

---

## PR26. Phase presets và experimental A2A adapter bridge
**Phụ thuộc:** PR25  
**Dựa trên tasks:** F24  
**Mục tiêu:** khóa nền V2 và chừa adapter bridge rõ cho V3

### Bao gồm
- migration cho `phases`
- phase presets nhẹ
- phase-aware relay templates
- experimental `A2AAdapter` layer riêng
- nếu cần, `a2a_tasks` mapping table
- tests cho phase transition và adapter mapping cơ bản

### Không bao gồm
- A2A public API production-grade
- dashboard web lớn

### Điều kiện merge
- session có thể chuyển phase
- relay có thể thay đổi theo phase preset
- adapter bridge tồn tại riêng, không làm bẩn Coordinator API

### Demo sau PR
- chạy một session theo preset planning → implementation → review và map được job nội bộ sang task model thử nghiệm

---

## 5. Mốc demo quan trọng

### Mốc G — sau PR19
Bạn có:

- `system/status`
- debug aggregates
- log đủ để vận hành coordinator sau MVP

### Mốc H — sau PR22
Bạn có:

- channels/views
- participant policy rõ hơn
- advanced jobs và offline queue tối thiểu

### Mốc I — sau PR25
Bạn có:

- rules engine cơ bản
- transcript export
- review mode đủ dùng

### Mốc J — sau PR26
Bạn có:

- V2 foundation đủ chắc
- phase presets nhẹ
- adapter bridge rõ cho V3

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:

- `pr/19-system-status`
- `pr/20-channels`
- `pr/21-roles-and-policies`
- `pr/22-advanced-jobs`
- `pr/23-rules-engine`
- `pr/24-artifacts-and-export`
- `pr/25-review-mode`
- `pr/26-phases-and-a2a-bridge`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:

- code chạy được local
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- không thêm dead code rõ ràng
- không mở rộng phạm vi PR quá đà
- có ít nhất một cách demo thủ công

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:

- đi theo đúng thứ tự PR19 → PR26
- không nhảy qua PR sau nếu PR trước chưa ổn

Nếu bạn làm theo sprint:

- gộp 2 PR nhỏ thành một sprint nội bộ
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `IMPLEMENTATION_TASKS_V2.md`:

- `IMPLEMENTATION_TASKS_V2.md` trả lời câu hỏi: **phải code module nào**
- `IMPLEMENTATION_ORDER_V2.md` trả lời câu hỏi: **nên merge theo thứ tự nào**

Tài liệu này là cầu nối từ roadmap V2 sang hành động thực tế sau MVP.
