# Thứ tự triển khai theo PR giai đoạn V5: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển định hướng `PLAN_V5.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V5.

Khác với `IMPLEMENTATION_ORDER_V4.md`:
- `IMPLEMENTATION_ORDER_V4.md` chốt **PR34-PR37** cho hardening, telemetry, release readiness và deployment readiness
- `IMPLEMENTATION_ORDER_V5.md` chốt **PR38-PR42** cho access boundary, thin operator UI, realtime operator surface, A2A interoperability và small-team deployment profile

Mục tiêu của tài liệu:
- cho biết sau V4 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review, verify và rollback dễ hơn
- tách rõ access boundary, UI shell, live event surface, interoperability và deployment packaging
- tránh gộp auth, UI, realtime streams, interop và deployment profile vào cùng một PR lớn

---

## 2. Nguyên tắc chia PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải làm hệ thống dễ dùng hơn mà không làm bẩn core coordinator model.**
3. **PR thêm access boundary, UI contract hoặc public interoperability phải thêm docs và tests cùng lúc.**
4. **PR sau chỉ bắt đầu khi PR trước đã merge hoặc đã ổn định cục bộ.**
5. **Không gộp auth/access boundary, UI shell, realtime event feed và deployment profile vào một PR duy nhất.**
6. **Ưu tiên dọc theo luồng adoption thật:** vào được an toàn → nhìn thấy được → theo dõi realtime được → tích hợp ngoài được → triển khai nhóm nhỏ được.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR38 → PR39 → PR40 → PR41 → PR42**

Không có PR nào bị cô lập:
- PR38 khóa boundary truy cập tối thiểu cho các surface sẽ được mở ra ở các PR sau
- PR39 tạo chỗ đứng cho UI trước khi thêm live activity và event-driven behavior
- PR40 biến UI từ “đọc được” thành “theo dõi được” bằng live/replay surface
- PR41 tận dụng public/event surface đã ổn định hơn để chốt interoperability path
- PR42 đóng gói deployment profile trên một surface đã đủ rõ cho operator và external integrator

---

## 4. Danh sách PR theo thứ tự triển khai

## PR38. Access boundary và external safety baseline

**Phụ thuộc:** PR37  
**Mục tiêu:** thêm lớp truy cập tối thiểu và cấu hình an toàn hơn cho operator/public surface mà vẫn giữ local-first path gọn

### Bao gồm
- auth/config hooks tối thiểu cho operator/public routes
- API key hoặc service token flow cơ bản
- phân tách rõ hơn trusted local path và protected external path nếu cần
- audit/log context cho access decisions và auth failures tối thiểu
- integration tests cho unauthorized / forbidden / allowed flows
- docs setup cho local-dev, trusted-demo và protected mode

### Không bao gồm
- SSO enterprise hoặc auth production-grade đầy đủ
- UI frontend lớn
- interoperability tests rộng

### Điều kiện merge
- operator/public surface có thể bật bảo vệ bằng config rõ ràng
- local-dev path vẫn chạy mượt với defaults hợp lý
- tests auth/access baseline pass
- docs giải thích được cách chạy ở các profile cơ bản

### Demo sau PR
- bật protected mode, gọi thử một operator/public route không có key và quan sát hệ thống trả về lỗi nhất quán; sau đó gọi lại với key hợp lệ và đi qua thành công

---

## PR39. Thin operator UI shell

**Phụ thuộc:** PR38  
**Mục tiêu:** dựng giao diện mỏng cho operator trên nền API hiện có để giảm việc ghép nhiều route thủ công khi vận hành

### Bao gồm
- UI shell tối thiểu cho sessions, transcript, jobs, phases, approvals và artifacts
- filters hoặc summary cards cơ bản theo session/status/runtime/template
- UI client/service layer bọc các APIs hiện có
- loading/error/empty states tối thiểu ở các view chính
- smoke tests hoặc UI tests cơ bản cho flow đọc chính
- docs setup/run cho UI local

### Không bao gồm
- live event stream đầy đủ trong UI
- product workflow lớn cho end user
- logic orchestration mới ở frontend

### Điều kiện merge
- operator mở UI và theo dõi được các đối tượng vận hành chính từ một chỗ
- UI không tạo thêm canonical state riêng lệch với backend
- các flow đọc chính pass smoke/test cơ bản
- docs setup UI đủ để người khác chạy lại

### Demo sau PR
- mở UI, chọn một session, xem transcript, jobs, approvals và artifacts mà không phải gọi nhiều route thủ công

---

## PR40. Realtime operator surface

**Phụ thuộc:** PR39  
**Mục tiêu:** cho operator thấy activity sống của session/job/phase/approval/runtime theo thời gian thực thay vì chỉ refresh thủ công

### Bao gồm
- live stream contract cho UI clients
- reconnect/replay hoặc since/cursor semantics tối thiểu
- activity feed hoặc timeline theo session
- hiển thị pending approvals, recent errors, stuck jobs và phase bottlenecks cơ bản
- integration tests cho live/replay behavior
- docs cho event semantics phía UI/operator

### Không bao gồm
- interoperability kit đầy đủ cho external integrator
- distributed realtime infra phức tạp
- product-grade notifications đa kênh

### Điều kiện merge
- UI nhận được event lifecycle chính theo thời gian thực
- reconnect hoặc reload không làm operator mù hoàn toàn với recent activity
- pending/stuck signals nhìn thấy được qua live surface
- tests live/replay pass

### Demo sau PR
- chạy một flow review hoặc approval, giữ UI mở và quan sát event feed cập nhật theo thời gian thực khi job đổi trạng thái và approval được tạo/resolve

---

## PR41. A2A interoperability và adoption kit

**Phụ thuộc:** PR40  
**Mục tiêu:** biến public/A2A surface từ trạng thái “đã mở” thành trạng thái “tích hợp được và verify được”

### Bao gồm
- hoàn thiện `/.well-known/agent-card.json` và discovery metadata
- docs mapping rõ hơn giữa internal model và public/A2A model
- interoperability smoke flow cho create task → stream status → read artifact/outcome
- compatibility tests cho public/A2A surface chính
- curl/script examples và quickstart cho external integrator
- troubleshooting notes cho public/A2A flows

### Không bao gồm
- multi-tenant public platform
- federation phức tạp giữa nhiều coordinator
- product auth đầy đủ cho bên thứ ba quy mô lớn

### Điều kiện merge
- external client/agent mẫu có thể tích hợp theo docs mà không cần đọc core code quá sâu
- discovery metadata hữu ích hơn placeholder tối thiểu
- public/A2A smoke flow pass end-to-end
- compatibility tests cho surface chính pass

### Demo sau PR
- dùng một script ngoài repo hoặc client mẫu để tạo task qua public surface, theo dõi event, rồi đọc outcome/artifact thành công

---

## PR42. Small-team deployment profile và release packaging

**Phụ thuộc:** PR41  
**Mục tiêu:** đóng gói một profile triển khai thực dụng cho nhóm nhỏ trên nền surface đã đủ rõ cho operator và external integrator

### Bao gồm
- profile config rõ cho local-dev, trusted-demo và small-team deployment
- persistence/dependency option phù hợp hơn cho profile nhóm nhỏ nếu cần
- cập nhật docs deployment, reverse proxy, secret handling, migration, backup/restore và rollback tối thiểu
- mở rộng smoke/release scripts cho profile mới
- cập nhật README, release docs, upgrade notes và STATUS cho V5 foundation

### Không bao gồm
- distributed coordinator
- enterprise SSO / IAM phức tạp
- full cloud platform automation

### Điều kiện merge
- có ít nhất một profile triển khai cho nhóm nhỏ với docs rõ và smoke path tương ứng
- release/smoke scripts phản ánh được profile mới
- local-first path cũ vẫn chạy được
- docs vận hành và docs release đồng bộ với code/config mới

### Demo sau PR
- chạy profile small-team theo docs, verify startup/readiness, thực hiện một smoke flow từ UI hoặc public surface rồi kiểm tra backup/restart path tối thiểu

---

## 5. Ghi chú về nhịp triển khai

- Sau mỗi PR nên cập nhật `STATUS.md` ngay thay vì chờ cuối phase.
- Với PR39 và PR40, nên giữ UI ở mức operator-first; chưa nên trượt thành web product lớn.
- Với PR41, cần ưu tiên demo path và docs trước khi tối ưu độ rộng của interoperability matrix.
- Với PR42, chỉ nên thêm deployment complexity khi có smoke/release gate đi kèm.

V5 hoàn tất khi hệ thống đi được trọn chuỗi: **protected access → usable operator UI → realtime visibility → verified interoperability → repeatable small-team deployment**.
