# Thứ tự triển khai theo PR giai đoạn V3: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `IMPLEMENTATION_TASKS_V3.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V3.

Khác với `IMPLEMENTATION_ORDER_V2.md`:

- `IMPLEMENTATION_ORDER_V2.md` chốt **PR19-PR26** cho V2 foundation
- `IMPLEMENTATION_ORDER_V3.md` chốt **PR27-PR33** cho V3

Mục tiêu của tài liệu:

- cho biết sau V2 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review dễ
- giữ public API, orchestration, runtime và policy tách lớp rõ ràng
- tránh gộp runtime isolation, dashboard và policy automation vào cùng một PR lớn

---

## 2. Nguyên tắc chia PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải để hệ thống tiến gần hơn tới public/orchestration surface rõ ràng.**
3. **PR thêm public contract thì phải thêm docs và tests cùng lúc.**
4. **PR sau chỉ bắt đầu khi PR trước đã merge hoặc đã ổn định cục bộ.**
5. **Không gộp A2A public API, runtime pools và advanced policy engine vào cùng một PR.**
6. **Ưu tiên dọc theo luồng dùng thật:** public task tạo được → theo dõi được → dùng template được → orchestration mạnh hơn → runtime isolation → dashboard/policy.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR27 → PR28 → PR29 → PR30 → PR31 → PR32 → PR33**

Không có PR nào bị cô lập:

- PR27 mở public contract cho các PR sau
- PR30 phụ thuộc session template và event surface trước đó
- PR33 tận dụng dashboard/runtime/orchestration state đã ổn định hơn

---

## 4. Danh sách PR theo thứ tự triển khai

## PR27. A2A public API v1
**Phụ thuộc:** PR26  
**Dựa trên tasks:** F25  
**Mục tiêu:** biến adapter bridge thử nghiệm thành contract public tối thiểu nhưng rõ ràng

### Bao gồm
- public task resource model
- create/list/get task routes
- status/error/artifact mapping từ internal model
- docs contract public
- integration tests cho task API

### Không bao gồm
- event subscriptions
- session templates
- runtime isolation

### Điều kiện merge
- external client tạo và đọc task được qua API public
- mapping job/task không làm bẩn Coordinator API
- tests public task pass

### Demo sau PR
- tạo public task mới và xem internal job được map ngược ra task payload

---

## PR28. Public subscribe/push event surface
**Phụ thuộc:** PR27  
**Dựa trên tasks:** F26  
**Mục tiêu:** public client theo dõi được task/status/artifact mà không polling thô

### Bao gồm
- subscription hoặc cursor model
- public event stream routes
- event types cơ bản cho task lifecycle
- replay tối thiểu theo cursor hoặc `since`
- integration tests cho stream/replay

### Không bao gồm
- session templates
- orchestration gates
- runtime pools

### Điều kiện merge
- client đọc được task event stream
- event ordering và replay cơ bản ổn định
- tests event stream pass

### Demo sau PR
- tạo task, chạy flow tối thiểu, quan sát stream nhận `created`, `status_changed`, `completed`

---

## PR29. Session templates và orchestration presets
**Phụ thuộc:** PR28  
**Dựa trên tasks:** F27  
**Mục tiêu:** session có thể khởi tạo từ preset collaboration thay vì cấu hình tay từng lần

### Bao gồm
- migration cho session templates
- repository/service/API cho templates
- templates mặc định
- instantiate session từ template
- tests cho template flow

### Không bao gồm
- gated review orchestration
- runtime pools
- operator dashboard

### Điều kiện merge
- session tạo từ template mang đúng roles/channels/phases/rules
- ít nhất một template chạy được end-to-end
- tests template pass

### Demo sau PR
- tạo session từ `implementation_review` và thấy preset được áp dụng đầy đủ

---

## PR30. Advanced review orchestration và phase gates
**Phụ thuộc:** PR29  
**Dựa trên tasks:** F28  
**Mục tiêu:** review/phase flow có gate và handoff rõ hơn, bớt phụ thuộc điều phối tay

### Bao gồm
- orchestration run/state tối thiểu
- gated phase transitions
- auto-create handoff jobs/artifacts
- integration tests cho review/revise/finalize flow

### Không bao gồm
- runtime pools
- dashboard aggregates
- advanced policy automation

### Điều kiện merge
- phase transition có gate rõ
- review/revise flow chạy được end-to-end
- tests orchestration pass

### Demo sau PR
- builder hoàn thành, reviewer reject, system tự tạo revise handoff đúng phase

---

## PR31. Runtime pools và isolated work contexts
**Phụ thuộc:** PR30  
**Dựa trên tasks:** F29  
**Mục tiêu:** execution được gán vào pool/context rõ ràng hơn khi workload hoặc agent count tăng

### Bao gồm
- migration cho runtime pools và work contexts
- assignment/fallback logic tối thiểu
- diagnostics cho pool utilization
- integration tests cho assignment/recovery

### Không bao gồm
- dashboard web lớn
- policy automation nâng cao

### Điều kiện merge
- job có thể gán vào pool/context theo policy cơ bản
- failure/recovery có đường nhìn rõ
- tests runtime pools pass

### Demo sau PR
- đưa một job vào pool phù hợp và quan sát fallback khi runtime không sẵn sàng

---

## PR32. Operator dashboard và debug expansion
**Phụ thuộc:** PR31  
**Dựa trên tasks:** F30  
**Mục tiêu:** operator thấy hệ thống đang tắc ở phase/runtime/review nào mà không tự tổng hợp thủ công

### Bao gồm
- dashboard-ready aggregate routes
- filters theo session/template/phase/runtime
- queue heat, review bottlenecks, runtime health, public throughput
- tests cho aggregate chính

### Không bao gồm
- advanced policy automation
- auth production-grade

### Điều kiện merge
- operator trả lời được “kẹt ở đâu” qua dashboard surface
- aggregates đủ ổn định để làm nền cho UI sau này
- tests dashboard pass

### Demo sau PR
- gọi dashboard APIs và nhìn thấy phase distribution cùng review bottlenecks

---

## PR33. Advanced policy engine và conditional automation
**Phụ thuộc:** PR32  
**Dựa trên tasks:** F31  
**Mục tiêu:** policy decisions được tự động hóa có điều kiện, giải thích được và có override rõ

### Bao gồm
- migration cho policy conditions
- policy engine v2
- conditional auto-approve / escalation
- operator pause/resume automation
- integration tests cho policy flows

### Không bao gồm
- cross-host distributed coordination
- multi-tenant production auth

### Điều kiện merge
- ít nhất một approval/review flow chịu tác động bởi policy engine v2
- policy decisions có audit trail rõ
- tests policy engine v2 pass

### Demo sau PR
- bật policy auto-approve theo template/phase và quan sát audit trail sinh ra đúng

---

## 5. Mốc demo quan trọng

### Mốc K — sau PR28
Bạn có:

- A2A public task API
- event subscribe/push model cơ bản

### Mốc L — sau PR30
Bạn có:

- session templates
- gated review/orchestration flow

### Mốc M — sau PR31
Bạn có:

- runtime pools
- isolated work contexts

### Mốc N — sau PR33
Bạn có:

- operator dashboard surface tốt hơn
- advanced policy automation
- V3 foundation đủ rõ để đi tiếp sang scale/public platform

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:

- `pr/27-a2a-public-api`
- `pr/28-a2a-event-stream`
- `pr/29-session-templates`
- `pr/30-orchestration-gates`
- `pr/31-runtime-pools`
- `pr/32-operator-dashboard`
- `pr/33-policy-engine-v2`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:

- code chạy được local
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- public contract không mập mờ
- không mở rộng phạm vi PR quá đà
- có ít nhất một cách demo thủ công

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:

- đi theo đúng thứ tự PR27 → PR33
- không nhảy qua PR sau nếu PR trước chưa ổn

Nếu bạn làm theo sprint:

- có thể gộp 2 PR nhỏ thành một sprint nội bộ
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `IMPLEMENTATION_TASKS_V3.md`:

- `IMPLEMENTATION_TASKS_V3.md` trả lời câu hỏi: **phải code module nào**
- `IMPLEMENTATION_ORDER_V3.md` trả lời câu hỏi: **nên merge theo thứ tự nào**

Tài liệu này là cầu nối từ roadmap V3 sang hành động thực tế sau khi V2 foundation đã khóa xong.
