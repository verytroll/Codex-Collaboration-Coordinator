# PLAN_V5.md

## 1. Mục tiêu của tài liệu

Tài liệu này chốt hướng phát triển sau khi **V4 foundation đã hoàn tất tại F35 / PR37**.

Khác với `docs/planning/archive/PLAN_V4.md`:
- `docs/planning/archive/PLAN_V4.md` tập trung **làm cứng hệ thống, đo được hệ thống và chuẩn bị phát hành/triển khai sạch hơn**
- `docs/planning/archive/PLAN_V5.md` tập trung **mở lớp sử dụng thật ở phía trên nền đã ổn định**: access boundary, thin operator UI, realtime operator surface, A2A interoperability rõ hơn và deployment profile dùng được cho nhóm nhỏ

Tài liệu này kế thừa và nên đọc cùng:
- `docs/reference/PRD.md`
- `docs/reference/ARCHITECTURE.md`
- `docs/reference/API.md`
- `docs/reference/DB_SCHEMA.md`
- `docs/planning/archive/PLAN.md`
- `docs/planning/archive/PLAN_V2.md`
- `docs/planning/archive/PLAN_V3.md`
- `docs/planning/archive/PLAN_V4.md`
- `docs/planning/STATUS.md`

---

## 2. Điểm xuất phát của V5

Sau V4, hệ thống đã có:
- A2A public API v1 và public event stream
- session templates, orchestration presets và phase gates
- runtime pools cùng isolated work contexts
- operator dashboard/debug surface
- advanced policy engine và conditional automation
- hardening, telemetry, release readiness và deployment readiness tối thiểu

Điểm còn thiếu để đi tiếp:
- operator hiện có API/debug surface khá tốt nhưng **chưa có thin operator UI đủ gọn** để dùng như một mặt điều khiển hằng ngày
- public/external surface đã mở nhưng **access boundary còn nên được chuẩn hóa rõ hơn** trước khi dùng ngoài local hoặc ngoài vòng phát triển hẹp
- event/telemetry đã có nhưng **trải nghiệm realtime cho operator** vẫn còn rời rạc giữa nhiều route và diagnostics view
- `/.well-known/agent-card.json` mới đang ở mức **A2A-ready discovery placeholder**, chưa chứng minh đầy đủ một interoperability path rõ với external client/agent
- deployment hiện vẫn chủ ý bảo thủ theo profile nhỏ: single FastAPI process, SQLite local volume và CodexBridge local mode; điều này tốt cho local-first nhưng **chưa đủ sạch cho nhóm nhỏ dùng lâu dài**

---

## 3. Mục tiêu của V5

V5 nên làm rõ 5 hướng:

1. Tạo **access boundary tối thiểu nhưng rõ** cho operator/public surface để hệ thống an toàn hơn khi dùng ngoài local loop.
2. Dựng **thin operator UI** trên các route và telemetry đã có thay vì viết lại logic vận hành ở frontend.
3. Mở **realtime operator surface** để session, job, phase, approval, artifact và runtime health được theo dõi theo luồng sống.
4. Nâng A2A từ mức “public surface có thể map được” lên mức **interoperability có thể demo và verify rõ**.
5. Chuẩn hóa **small-team deployment profile** để hệ thống dễ được dùng lặp lại trong môi trường nhóm nhỏ mà không nhảy ngay sang multi-tenant/distributed platform.

---

## 4. Phạm vi của V5

### 4.1 Trong phạm vi

V5 ưu tiên các hướng sau:

1. access boundary và external safety baseline:
   - API key hoặc service token tối thiểu
   - auth hooks rõ cho operator/public routes
   - safer defaults cho môi trường non-local
   - audit/log context cho access decisions tối thiểu

2. thin operator UI:
   - danh sách session, participant, transcript, jobs, phases, approvals, artifacts
   - filters cơ bản theo session/template/status/runtime
   - detail views mỏng cho diagnostics chính
   - UI bám public/internal API có sẵn thay vì thêm orchestration logic mới ở frontend

3. realtime operator surface:
   - live stream cho message/job/phase/review/approval/runtime events
   - event timeline hoặc activity feed cho session
   - reconnect/replay tối thiểu theo cursor hoặc since
   - UI/state model cho recent activity và stuck-flow detection cơ bản

4. A2A interoperability:
   - hoàn thiện discovery metadata và `agent-card`
   - interoperability tests hoặc compatibility smoke flows
   - demo flow giữa coordinator và external A2A-style client/agent
   - docs mapping rõ giữa internal model và public/A2A model

5. deployment profile cho nhóm nhỏ:
   - profile DB bền hơn tùy chọn ngoài SQLite nếu cần
   - config profile rõ cho local / demo / small-team deployment
   - reverse proxy / startup / migration / backup notes rõ hơn
   - release packaging và smoke path phù hợp với profile mới

### 4.2 Ngoài phạm vi

Các phần sau chưa phải trọng tâm của V5:
- web product hoàn chỉnh cho end user
- auth production-grade đầy đủ, SSO enterprise hoặc IAM phức tạp
- multi-tenant cloud platform hoàn chỉnh
- distributed coordinator hoặc cross-host federation phức tạp
- fork sâu vào Codex runtime
- UI nặng về product workflow vượt quá nhu cầu operator/adoption ban đầu

---

## 5. Nguyên tắc triển khai cho V5

1. **UI đứng trên API hiện có.** Không đẩy orchestration, routing hoặc policy logic vào frontend.
2. **Coordinator-first vẫn giữ nguyên.** V5 chỉ mở lớp sử dụng và external adoption trên nền điều phối trung tâm đã có.
3. **Auth bọc quanh contract hiện có.** Nếu thêm access boundary, ưu tiên wrap route/service hiện tại thay vì viết lại flow chính.
4. **Event-first cho trải nghiệm realtime.** Operator UI nên dùng stream/replay thay vì polling thô càng nhiều càng tốt.
5. **Interoperability phải kiểm chứng được.** Mọi tuyên bố “A2A-ready” ở V5 nên đi kèm docs, smoke flow và tests tương ứng.
6. **Local-first vẫn là mặc định.** Mọi profile mới cho nhóm nhỏ không được làm hỏng trải nghiệm local/dev vốn là nền hiện tại.
7. **PR nhỏ, rủi ro cô lập.** Không gộp auth, UI shell, realtime surface, A2A interop và deployment profile vào một PR lớn.

---

## 6. Trình tự triển khai cấp cao

Dự án ở V5 nên đi qua 5 giai đoạn: **G21 → G22 → G23 → G24 → G25**

Trong đó:
- **G21** khóa access boundary và external safety baseline
- **G22** dựng thin operator UI shell trên API/telemetry hiện có
- **G23** thêm realtime event-driven operator surface
- **G24** chốt A2A interoperability và adoption kit
- **G25** chuẩn hóa deployment profile cho nhóm nhỏ và release packaging tương ứng

Phụ thuộc:
- G22 phụ thuộc G21 vì UI không nên mở rộng trước khi có boundary truy cập tối thiểu
- G23 phụ thuộc G22 vì live surface nên được gắn vào UI shell đã có chỗ hiển thị rõ ràng
- G24 phụ thuộc G23 vì interoperability demo nên tận dụng live/event surface đã ổn định hơn
- G25 phụ thuộc G24 vì deployment profile cho nhóm nhỏ nên đóng gói trên một external/adoption surface đã rõ contract

---

## 7. Kế hoạch chi tiết theo giai đoạn

## G21. Access boundary và external safety baseline

**Phụ thuộc:** G20 / F35  
**Mở khóa:** G22  
**Kết quả:** operator/public surface có lớp truy cập tối thiểu, cấu hình rõ và an toàn hơn khi dùng ngoài local loop

### Công việc
1. Tạo auth/config hooks tối thiểu cho operator/public routes:
   - API key hoặc service token
   - môi trường bật/tắt rõ theo config profile
2. Tách route nội bộ, route operator và route public rõ hơn nếu cần
3. Gắn audit/log context tối thiểu cho access decisions và failed auth attempts
4. Viết docs cho chế độ local-dev, trusted-demo và small-team exposure
5. Viết integration tests cho unauthorized / forbidden / allowed flows tối thiểu

### Tiêu chí xong
- operator/public surface có thể được bảo vệ bằng cấu hình rõ ràng
- local-dev path vẫn chạy gọn, không bị auth mới làm nặng quá mức
- docs giải thích được cách bật/tắt boundary theo profile môi trường

## G22. Thin operator UI shell

**Phụ thuộc:** G21  
**Mở khóa:** G23  
**Kết quả:** operator có một giao diện mỏng nhưng dùng được cho các thao tác quan sát và điều phối thường ngày

### Công việc
1. Tạo UI shell tối thiểu cho:
   - sessions
   - participants
   - messages / transcript
   - jobs / phases
   - approvals
   - artifacts
2. Thêm filters và summary cards cơ bản theo session/status/runtime/template
3. Bọc các APIs hiện có thành client/service layer phía UI mà không làm lộ logic điều phối vào frontend
4. Chuẩn hóa error/loading/empty states ở mức vận hành tối thiểu
5. Viết docs setup UI local và tests cơ bản cho UI flows chính

### Tiêu chí xong
- operator có thể theo dõi một session đang chạy mà không phải ghép nhiều route thủ công
- UI dùng được trên nền routes hiện có mà không làm bẩn coordinator model
- các flow đọc chính có smoke path hoặc test cơ bản

## G23. Realtime operator surface

**Phụ thuộc:** G22  
**Mở khóa:** G24  
**Kết quả:** operator nhìn thấy activity sống của session/job/phase/approval/runtime theo luồng thời gian thực

### Công việc
1. Chuẩn hóa live stream contract cho UI:
   - message events
   - job lifecycle events
   - phase/review/approval events
   - runtime health/activity events
2. Thêm reconnect, replay hoặc since/cursor semantics tối thiểu cho UI clients
3. Tạo activity timeline hoặc event feed theo session
4. Hiển thị recent errors, stuck jobs, pending approvals và phase bottlenecks rõ hơn trong UI
5. Viết integration tests cho live/replay behavior và docs cho event semantics

### Tiêu chí xong
- operator theo dõi được một flow đang chạy theo thời gian thực
- khi UI reconnect, recent state không bị mù hoàn toàn
- stuck flow hoặc pending approval có tín hiệu nhìn thấy nhanh hơn qua activity surface

## G24. A2A interoperability và adoption kit

**Phụ thuộc:** G23  
**Mở khóa:** G25  
**Kết quả:** hệ thống không chỉ “A2A-ready” theo kiến trúc mà còn có interoperability path có thể demo, verify và tài liệu hóa

### Công việc
1. Hoàn thiện `agent-card` và discovery metadata ở mức hữu ích thực tế hơn
2. Chuẩn hóa ví dụ request/response, versioning notes và mapping docs cho external client
3. Viết interoperability smoke flow:
   - external client tạo task
   - theo dõi event/status
   - đọc artifact hoặc completion outcome
4. Bổ sung compatibility tests cho public/A2A surface quan trọng
5. Tạo adoption kit tối thiểu:
   - curl / script examples
   - quickstart cho external integrator
   - failure notes / troubleshooting cho public flows

### Tiêu chí xong
- một external client/agent mẫu có thể tích hợp theo docs mà không cần đọc code lõi quá sâu
- public/A2A claims có demo path và tests tương ứng
- discovery metadata không còn chỉ là placeholder mang tính báo trước

## G25. Small-team deployment profile và release packaging

**Phụ thuộc:** G24  
**Kết quả:** hệ thống có profile triển khai thực dụng cho nhóm nhỏ, lặp lại được và không làm mất local-first path

### Công việc
1. Thêm profile cấu hình rõ cho:
   - local-dev
   - trusted-demo
   - small-team deployment
2. Bổ sung persistence/dependency options phù hợp hơn cho small-team profile nếu cần
3. Cập nhật deployment docs cho reverse proxy, secret handling, migration, backup/restore và rollback tối thiểu
4. Mở rộng smoke/release scripts để phản ánh profile mới
5. Cập nhật release notes, upgrade notes, README và STATUS cho V5 foundation

### Tiêu chí xong
- có ít nhất một deployment profile dùng được cho nhóm nhỏ với docs rõ ràng
- release/smoke path phản ánh đúng profile mới thay vì chỉ local conservative profile
- local-first setup cũ vẫn chạy được và không bị regression rõ rệt

---

## 8. Kết quả kỳ vọng sau V5

Sau V5, Codex Collaboration Coordinator nên đạt được trạng thái sau:
- có lớp truy cập tối thiểu đủ rõ để mở operator/public surface an toàn hơn
- có thin operator UI dùng được hằng ngày cho quan sát và điều phối cơ bản
- có realtime event surface rõ cho operator thay vì chỉ đọc aggregate/debug route rời rạc
- có A2A interoperability path có docs, demo và tests rõ hơn
- có deployment profile cho nhóm nhỏ đủ sạch để adoption thực tế tốt hơn

V5 thành công khi hệ thống **không chỉ ổn định về nội tạng** như V4, mà còn **dễ được dùng, dễ được tích hợp và dễ được mang ra ngoài local loop** mà không phá kiến trúc coordinator-first hiện có.
