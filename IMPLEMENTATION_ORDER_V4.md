# Thứ tự triển khai theo PR giai đoạn V4: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `IMPLEMENTATION_TASKS_V4.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V4.

Khác với `IMPLEMENTATION_ORDER_V3.md`:

- `IMPLEMENTATION_ORDER_V3.md` chốt **PR27-PR33** cho V3 foundation
- `IMPLEMENTATION_ORDER_V4.md` chốt **PR34-PR37** cho V4 hardening, telemetry, release readiness và deployment readiness

Mục tiêu của tài liệu:

- cho biết sau V3 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review, verify và rollback dễ hơn
- tách rõ reliability, observability, release discipline và deployment surface
- tránh gộp hardening, telemetry, release prep và deployment packaging vào cùng một PR lớn

---

## 2. Nguyên tắc chia PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải làm hệ thống an toàn vận hành hơn hoặc dễ quan sát hơn.**
3. **PR thêm diagnostics, telemetry hoặc deployment contract phải thêm docs và tests cùng lúc.**
4. **PR sau chỉ bắt đầu khi PR trước đã merge hoặc đã ổn định cục bộ.**
5. **Không gộp hardening sâu, telemetry và release/deployment prep vào một PR duy nhất.**
6. **Ưu tiên dọc theo luồng vận hành thật:** fail có kiểm soát → đo được → phát hành lặp lại được → triển khai sạch hơn.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR34 → PR35 → PR36 → PR37**

Không có PR nào bị cô lập:

- PR34 khóa failure boundary và recovery path cho các PR sau
- PR35 dựa trên flow đã ổn định hơn để thêm telemetry đáng tin
- PR36 tận dụng telemetry và scripts ổn định hơn để chốt release discipline
- PR37 đóng gói deployment surface trên một release candidate đã có checklist và runbook rõ

---

## 4. Danh sách PR theo thứ tự triển khai

## PR34. Hardening và reliability
**Phụ thuộc:** PR33  
**Dựa trên tasks:** F32  
**Mục tiêu:** làm cứng các flow public/orchestration/runtime quan trọng để fail có kiểm soát và recovery path rõ hơn

### Bao gồm
- validation và error mapping cho public/orchestration/policy surface
- idempotency hoặc duplicate-action guards tối thiểu
- timeout/cancellation/cleanup/fallback boundaries quanh CodexBridge và runtime pools
- integration tests cho recovery, replay, retry và edge cases
- troubleshooting notes cho failure modes chính

### Không bao gồm
- telemetry theo thời gian
- release checklist đầy đủ
- deployment packaging

### Điều kiện merge
- các lỗi ở surface chính trả về nhất quán hơn
- retry/replay không tạo duplicate state cơ bản
- bridge/runtime failure có đường fallback hoặc cleanup rõ
- tests hardening/recovery pass

### Demo sau PR
- mô phỏng retry, replay hoặc runtime failure và quan sát hệ thống giữ state nhất quán hơn

---

## PR35. Telemetry và observability
**Phụ thuộc:** PR34  
**Dựa trên tasks:** F33  
**Mục tiêu:** cho operator biết hệ thống đang chậm hoặc fail ở đâu theo thời gian thay vì chỉ thấy aggregate snapshot

### Bao gồm
- structured logging với correlation IDs hoặc request IDs
- telemetry counters hoặc metrics tối thiểu cho queue/job/phase/review/runtime/public task
- tách aggregate health với live/recent telemetry
- mở rộng operator/debug surfaces cho latency, bottleneck và failure hotspot
- tests cho correlation và telemetry-facing APIs
- docs cho semantics của logs/metrics/telemetry views

### Không bao gồm
- release gate đầy đủ
- deployment profile
- UI trực quan mới

### Điều kiện merge
- có thể nối từ request sang job/phase/runtime bằng correlation ID
- operator trả lời được “chậm ở đâu” và “fail ở đâu” qua telemetry surface
- CodexBridge health không còn chỉ là aggregate snapshot
- tests telemetry pass

### Demo sau PR
- chạy một flow có lỗi hoặc độ trễ và truy vết được bằng correlation ID cùng telemetry aggregates

---

## PR36. Release readiness và operational safety
**Phụ thuộc:** PR35  
**Dựa trên tasks:** F34  
**Mục tiêu:** tạo release candidate theo checklist lặp lại được, có runbook và smoke gate rõ

### Bao gồm
- release checklist cho test/lint/smoke/migration verification
- chuẩn hóa scripts và command path cho release gate
- runbook startup, incident triage, backup/restore và recovery tối thiểu
- cập nhật release notes, upgrade notes, README, STATUS và docs vận hành
- acceptance hoặc smoke checks đại diện cho release candidate

### Không bao gồm
- deployment topology đầy đủ
- multi-environment packaging phức tạp
- UI hoặc auth production-grade

### Điều kiện merge
- release candidate có thể được dựng theo checklist lặp lại được
- runbook đủ để người khác startup và recovery ở mức cơ bản
- docs vận hành và release docs đồng bộ
- smoke/release gate pass

### Demo sau PR
- chạy release checklist từ scripts/docs và dựng được release candidate theo quy trình rõ

---

## PR37. Deployment surface và external readiness
**Phụ thuộc:** PR36  
**Dựa trên tasks:** F35  
**Mục tiêu:** chuẩn hóa surface triển khai tối thiểu và guardrails cơ bản để hệ thống sẵn sàng hơn cho môi trường ngoài local

### Bao gồm
- deployment profile tối thiểu hoặc packaging/container path
- startup/readiness contract và migration strategy khi boot
- guardrails cơ bản cho config/access/defaults ở môi trường ngoài local
- docs topology triển khai tối thiểu và operational assumptions
- tests hoặc smoke checks cho deployment readiness

### Không bao gồm
- multi-tenant cloud platform
- distributed coordinator
- operator/product UI đầy đủ

### Điều kiện merge
- có ít nhất một deployment profile được mô tả và verify ở mức cơ bản
- health/readiness/startup contract rõ ràng hơn
- môi trường ngoài local có guardrails tốt hơn mặc định hiện tại
- deployment docs và checks pass

### Demo sau PR
- chạy hệ thống theo deployment profile tối thiểu và xác nhận startup/readiness/migration path hoạt động đúng

---

## 5. Mốc demo quan trọng

### Mốc O — sau PR34
Bạn có:

- failure boundaries rõ hơn
- recovery path rõ hơn cho bridge/runtime/retry flows

### Mốc P — sau PR35
Bạn có:

- telemetry theo thời gian
- correlation IDs và diagnostics đủ để truy vết bottleneck

### Mốc Q — sau PR36
Bạn có:

- release checklist rõ
- runbook vận hành cơ bản
- smoke/release gate lặp lại được

### Mốc R — sau PR37
Bạn có:

- deployment profile tối thiểu
- external readiness tốt hơn
- nền đủ sạch để bước sang UI mỏng hoặc adoption rộng hơn

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:

- `pr/34-hardening-reliability`
- `pr/35-telemetry-observability`
- `pr/36-release-readiness`
- `pr/37-deployment-readiness`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:

- code chạy được local
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- failure/telemetry/deployment contract không mập mờ
- không mở rộng phạm vi PR quá đà
- có ít nhất một cách demo thủ công

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:

- đi theo đúng thứ tự PR34 → PR37
- không nhảy sang PR sau nếu PR trước chưa ổn

Nếu bạn làm theo sprint:

- có thể gộp 2 PR nhỏ thành một sprint nội bộ
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `IMPLEMENTATION_TASKS_V4.md`:

- `IMPLEMENTATION_TASKS_V4.md` trả lời câu hỏi: **phải code module nào**
- `IMPLEMENTATION_ORDER_V4.md` trả lời câu hỏi: **nên merge theo thứ tự nào**

Tài liệu này là cầu nối từ roadmap V4 sang hành động thực tế sau khi V3 foundation đã khóa xong.
