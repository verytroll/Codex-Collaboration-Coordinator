# STATUS.md

### Trạng thái hiện tại
- **Ngày cập nhật:** 2026-03-31
- **Pha hiện tại:** F13 hoàn thành
- **Đang tập trung vào:** F14 - Relay engine và command handlers
- **Người thực hiện:** Codex

### Đang làm
- [ ] F14 — Relay engine và command handlers
- [ ] PR13 — Relay engine thực thi job qua CodexBridge

### Vừa hoàn thành
- [x] F13 — Message parser, mention router và job creation — 2026-03-31
- [x] PR12 — Message parser, mention detection và job creation — 2026-03-31
- [x] F12 — Runtime service và session-thread mapping — 2026-03-31
- [x] PR11 — Runtime service và session-thread mapping — 2026-03-31
- [x] F11 — Dựng CodexBridge process manager và JSON-RPC client — 2026-03-31
- [x] PR10 — Dựng CodexBridge process manager và JSON-RPC client — 2026-03-31
- [x] F10 — Tạo Participant API, Message API và event log cơ bản — 2026-03-31
- [x] PR09 — Participant API, Message API và session event log — 2026-03-31
- [x] F09 — Tạo Session API và Agent API cơ bản — 2026-03-31
- [x] PR08 — Session API và Agent API cơ bản — 2026-03-31
- [x] F08 — Tạo repository layer cho message và job — 2026-03-31
- [x] PR07 — Repository layer cho message, job, artifact, approval, presence — 2026-03-31
- [x] F07 — Tạo repository layer cho session và agent — 2026-03-31
- [x] PR06 — Repository layer cho session và agent — 2026-03-31
- [x] F06 — Tạo migration cho nhóm bảng runtime và lịch sử — 2026-03-31
- [x] PR05 — Tạo schema nhóm bảng runtime và lịch sử — 2026-03-31
- [x] PR04 — Tạo schema nhóm bảng nền — 2026-03-31
- [x] F05 — Tạo migration cho nhóm bảng nền — 2026-03-31
- [x] PR03 — Thiết lập kết nối DB và migration framework — 2026-03-31
- [x] F04 — Thiết lập migration framework — 2026-03-31
- [x] PR02 — Hoàn thiện toolchain và core app modules — 2026-03-31
- [x] F03 — Tạo core app modules — 2026-03-31
- [x] F02 — Cấu hình toolchain và chất lượng mã nguồn — 2026-03-31
- [x] F01 — Tạo skeleton dự án — 2026-03-31
- [x] PR01 — Tạo skeleton repo và app chạy được — 2026-03-31

### Tiếp theo
- [ ] F14 — Relay engine và command handlers
- [ ] PR13 — Relay engine thực thi job qua CodexBridge

### Blockers / Rủi ro
- Không có

### Ghi chú quyết định gần đây
- Quyết định: Repository session/agent/runtime/participant dùng async API bọc SQLite sync work trong thread.
- Lý do: Giữ code không block event loop nhưng vẫn không cần thêm dependency mới.
- Ảnh hưởng: CRUD tests có thể chạy trực tiếp trên SQLite migration thật.
- Quyết định: Participant và message API giai đoạn đầu chỉ thực hiện membership check, ghi event log và lưu message chat cơ bản.
- Lý do: PR09 cần có thể demo session chat trước khi thêm mention routing và relay ở các pha sau.
- Ảnh hưởng: route message hiện chưa tự sinh job từ mention.
- Quyết định: CodexBridge giai đoạn đầu dùng subprocess stdio + JSON-RPC line protocol với mock smoke test.
- Lý do: Khớp kiến trúc local-first và đủ để khóa contract bridge trước khi nối runtime thật.
- Ảnh hưởng: F11 có thể kiểm tra initialize/thread/turn flow mà chưa cần Codex runtime thật.
- Quyết định: Session-thread mapping giai đoạn đầu dùng state service trong memory, còn runtime status đi qua repository.
- Lý do: Tránh mở thêm schema/migration trong F12 nhưng vẫn có thể demo create/reuse thread ngay.
- Ảnh hưởng: F12 khóa được contract `thread/start`/`thread/resume` trước khi sang parser/router.
- Quyết định: Mention routing giai đoạn đầu phân giải `#agent` theo participant đang active và tạo job queued nội bộ.
- Lý do: F13 cần khóa được flow message -> mention -> job trước khi sang relay thực thi Codex.
- Ảnh hưởng: Message command bắt đầu bằng `/` được nhận diện trước routing, còn mention hợp lệ mới sinh job.

### Liên kết tài liệu liên quan
- `PLAN.md`
- `IMPLEMENTATION_TASKS.md`
- `IMPLEMENTATION_ORDER.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
