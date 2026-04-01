# Thứ tự triển khai theo PR giai đoạn V6: Codex Collaboration Coordinator

## 1. Mục tiêu của tài liệu

Tài liệu này chuyển `PLAN_V6.md` thành **thứ tự triển khai thực chiến theo PR nhỏ** cho V6.

Khác với `IMPLEMENTATION_ORDER_V5.md`:
- `IMPLEMENTATION_ORDER_V5.md` chốt **PR38-PR42** cho access boundary, thin operator UI, realtime operator surface, A2A interoperability và small-team deployment
- `IMPLEMENTATION_ORDER_V6.md` chốt **PR43-PR48** cho release closure, operator actions, team RBAC, durable runtime, realtime streaming và interop certification

Mục tiêu của tài liệu:
- cho biết sau V5 thì PR nào nên làm trước
- giữ mỗi PR đủ nhỏ để review, verify và rollback dễ hơn
- tách rõ release closure, write-actions, authorization, durability, streaming và interop proof
- tránh gộp control-plane capabilities vào một PR lớn khó kiểm soát

---

## 2. Nguyên tắc sắp thứ tự PR

1. **Mỗi PR chỉ có một mục tiêu chính.**
2. **PR nào cũng phải làm hệ thống an toàn vận hành hơn, bền hơn hoặc kiểm chứng được hơn.**
3. **PR thêm action surface phải đi kèm audit trail, docs và tests cho preconditions/failure modes.**
4. **PR thêm authorization phải dựa trên action verbs đã rõ, không thiết kế role model trong chân không.**
5. **PR thêm runtime durability phải giữ migration path rõ từ profile nhỏ hiện có.**
6. **PR thêm streaming phải giữ replay/debug path sẵn có thay vì thay thế đột ngột.**
7. **PR thêm compatibility claims phải đi cùng contract tests thực sự chạy được.**
8. **Ưu tiên theo luồng dùng thật:** release baseline rõ → operator can thiệp được → actor boundary rõ → runtime bền hơn → realtime transport thật → external contract được chứng minh.

---

## 3. Sơ đồ phụ thuộc cấp PR

**PR43 → PR44 → PR45 → PR46 → PR47 → PR48**

Không có PR nào bị cô lập:
- **PR43** khóa release baseline và version discipline cho các PR sau
- **PR44** xác định action surface thật để PR45 có thể đặt auth/role checks đúng chỗ
- **PR45** làm rõ actor/role boundary để PR46 xây durable runtime và worker semantics an toàn hơn
- **PR46** ổn định persistence/runtime delivery semantics để PR47 mở streaming contract đáng tin hơn
- **PR47** ổn định public realtime transport để PR48 chốt interop certification và compatibility matrix

---

## 4. Danh sách PR theo thứ tự triển khai

## PR43. V5 release closure

**Phụ thuộc:** PR42  
**Dựa trên tasks:** F41  
**Mục tiêu:** chốt V5 thành release milestone rõ với version, notes, verification và baseline regression

### Bao gồm
- version bump và release metadata
- release notes / upgrade notes cho V5
- release checklist và smoke verification cho package/release artifact
- docs đồng bộ giữa README, STATUS và deployment/release notes
- tag/release script cleanup nếu cần

### Không bao gồm
- operator write actions mới
- RBAC mới
- runtime architecture change

### Điều kiện merge
- có release notes rõ cho V5
- smoke/release verification chạy lại được
- versioning/docs không mâu thuẫn nhau
- baseline regression path rõ cho PR sau

### Demo sau PR
- tạo release candidate cục bộ hoặc nội bộ và chạy lại checklist từ package đến smoke flow

---

## PR44. Operator actions và audit trail

**Phụ thuộc:** PR43  
**Dựa trên tasks:** F42  
**Mục tiêu:** nâng operator shell thành operator console tối thiểu có thể tác động vào flow thật với guardrails rõ

### Bao gồm
- operator write endpoints hoặc command handlers cho `approve`, `reject`, `retry`, `resume`, `cancel`
- UI actions tối thiểu cho các thao tác trên
- precondition validation, conflict/error mapping và reason capture
- audit trail theo actor/action/target/time
- tests cho happy path, forbidden path, conflict path và retry path
- docs cho action semantics và operator expectations

### Không bao gồm
- team role model đầy đủ
- worker split lớn
- streaming transport mới

### Điều kiện merge
- operator có thể thực hiện ít nhất tập action cốt lõi trên UI hoặc API
- action sai precondition bị chặn rõ và trả lỗi nhất quán
- mọi write action quan trọng đều được audit
- regression tests cho action flows pass

### Demo sau PR
- thực hiện approve/retry/cancel trên một session thật và quan sát state đổi đúng cùng audit trail tương ứng

---

## PR45. Identity và team RBAC cơ bản

**Phụ thuộc:** PR44  
**Dựa trên tasks:** F43  
**Mục tiêu:** gắn actor identity và role checks tối thiểu cho các action ghi state quan trọng

### Bao gồm
- actor identity model tối giản
- role model cho `operator`, `reviewer`, `integration_client`
- authorization layer cho operator/public write actions
- audit enrichment theo actor/role
- config và docs cho trust model / access assumptions
- tests cho allowed/forbidden role paths

### Không bao gồm
- enterprise SSO
- organization hierarchy phức tạp
- policy authoring UI lớn

### Điều kiện merge
- action ghi state quan trọng đều có actor identity
- role checks chặn được ít nhất các thao tác sai vai trò chính
- docs giải thích rõ mode/access assumptions
- tests authz pass và không làm vỡ profile `local` / `trusted` hiện có

### Demo sau PR
- mô phỏng 2 actor với vai trò khác nhau và chứng minh một actor được phép thao tác còn actor kia bị từ chối có audit rõ

---

## PR46. Durable runtime và persistence profile

**Phụ thuộc:** PR45  
**Dựa trên tasks:** F44  
**Mục tiêu:** nâng hệ thống từ runtime/persistence kiểu local-first sang boundary bền hơn cho small-team dùng thật

### Bao gồm
- PostgreSQL profile rõ ràng
- migration, backup/restore và recovery notes cho profile mới
- worker split hoặc background execution boundary tối thiểu
- outbox/inbox hoặc durable queue pattern tối thiểu
- tests cho restart/resume/re-delivery/recovery
- docs topology và operational assumptions cho profile bền hơn

### Không bao gồm
- distributed multi-node scheduler
- autoscaling phức tạp
- cloud-managed platform đầy đủ

### Điều kiện merge
- profile durable mới boot được sạch và chạy smoke pass
- restart/recovery không làm vỡ state chính ở flow cốt lõi
- migration path từ SQLite profile hiện có được mô tả rõ
- tests recovery/delivery pass

### Demo sau PR
- chạy flow có background work, restart một thành phần rồi quan sát hệ thống tiếp tục hoặc recover được mà không nhân đôi state chính

---

## PR47. Realtime streaming transport

**Phụ thuộc:** PR46  
**Dựa trên tasks:** F45  
**Mục tiêu:** cung cấp transport realtime rõ hơn polling/replay cho operator và clients nhưng vẫn giữ replay/debug path

### Bao gồm
- SSE hoặc WebSocket transport cho activity/events
- cursor resume / reconnect semantics
- stream envelope và event docs rõ
- duplicate/backpressure/window handling tối thiểu
- tests cho reconnect, cursor continuity và duplicate delivery
- UI wiring tối thiểu để tận dụng transport mới

### Không bao gồm
- external event bus bắt buộc
- distributed streaming infrastructure lớn
- dashboard/product UI lớn

### Điều kiện merge
- operator/client có thể nhận updates realtime qua transport mới
- reconnect/cursor resume hoạt động nhất quán ở flow chính
- replay path cũ vẫn còn dùng được cho debug/fallback
- tests streaming pass

### Demo sau PR
- mở operator view, tạo activity mới và quan sát updates tới gần realtime; sau đó ngắt kết nối và reconnect với cursor để tiếp tục stream

---

## PR48. Interop certification và external adoption

**Phụ thuộc:** PR47  
**Dựa trên tasks:** F46  
**Mục tiêu:** chốt một compatibility surface hẹp nhưng đáng tin cho public API, public events và A2A bridge

### Bao gồm
- contract tests cho public API / public events / A2A bridge surface
- compatibility matrix được hỗ trợ chính thức
- sample clients / fixtures / adoption docs
- docs cho auth, streaming, deployment và client expectations
- V6 release candidate notes

### Không bao gồm
- universal protocol translation
- marketplace integration ecosystem
- broad enterprise support claims vượt quá phạm vi test

### Điều kiện merge
- contract tests chạy pass trên supported surface
- compatibility matrix và docs không over-claim
- sample clients chạy được theo docs
- V6 release candidate đủ rõ để verify nội bộ hoặc public alpha

### Demo sau PR
- chạy sample external client qua supported auth + streaming path và chứng minh contract surface hoạt động end-to-end theo docs

---

## 5. Mốc giá trị sau từng PR

### Mốc S — sau PR43
Bạn có:
- V5 được chốt thành release baseline rõ
- versioning, notes và verification path đồng bộ hơn

### Mốc T — sau PR44
Bạn có:
- operator không chỉ xem mà còn thao tác được trên flow thật
- action audit trail cơ bản

### Mốc U — sau PR45
Bạn có:
- identity và role checks tối thiểu cho write actions
- trust model rõ hơn cho môi trường nhiều người dùng nội bộ

### Mốc V — sau PR46
Bạn có:
- persistence/runtime boundary bền hơn
- recovery semantics tốt hơn cho team deployment

### Mốc W — sau PR47
Bạn có:
- realtime transport rõ hơn polling
- operator/client experience tốt hơn mà vẫn giữ replay/debug path

### Mốc X — sau PR48
Bạn có:
- compatibility surface hẹp nhưng đáng tin
- nền đủ sạch để bước sang V7 productization hoặc wider adoption

---

## 6. Gợi ý nhánh Git

Mỗi PR nên dùng một nhánh riêng, ví dụ:
- `pr/43-v5-release-closure`
- `pr/44-operator-actions-audit`
- `pr/45-team-rbac`
- `pr/46-durable-runtime`
- `pr/47-realtime-streaming`
- `pr/48-interop-certification`

---

## 7. Checklist cho mỗi PR

Trước khi merge, mỗi PR nên tự kiểm tra:
- code chạy được local
- test mới pass
- test cũ không vỡ
- docs liên quan đã cập nhật
- migration/auth/action/streaming contract không mập mờ
- có ít nhất một cách demo thủ công
- không mở rộng phạm vi PR quá đà

---

## 8. Cách dùng tài liệu này

Nếu bạn làm một mình:
- đi theo đúng thứ tự **PR43 → PR48**
- không nhảy sang PR46 hoặc PR47 nếu PR44/PR45 chưa ổn

Nếu bạn làm theo sprint:
- có thể gộp **PR43 + PR44** thành một sprint nội bộ
- có thể gộp **PR47 + PR48** thành sprint chốt release candidate
- nhưng vẫn giữ commit và review theo từng PR nhỏ

Nếu bạn dùng cùng `PLAN_V6.md`:
- `PLAN_V6.md` trả lời câu hỏi: **phase V6 nhằm giải quyết vấn đề gì**
- `IMPLEMENTATION_ORDER_V6.md` trả lời câu hỏi: **nên merge theo thứ tự nào**
