# STATUS.md

### Trạng thái hiện tại
- **Ngày cập nhật:** 2026-03-31
- **Pha hiện tại:** F08 hoàn thành
- **Đang tập trung vào:** F09 - Session API và Agent API cơ bản
- **Người thực hiện:** Codex

### Đang làm
- [ ] F09 — Tạo Session API và Agent API cơ bản
- [ ] PR08 — Session API và Agent API cơ bản

### Vừa hoàn thành
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
- [ ] F09 — session, agent API cơ bản
- [ ] PR08 — Session API và Agent API cơ bản

### Blockers / Rủi ro
- Không có

### Ghi chú quyết định gần đây
- Quyết định: Repository session/agent/runtime/participant dùng async API bọc SQLite sync work trong thread.
- Lý do: Giữ code không block event loop nhưng vẫn không cần thêm dependency mới.
- Ảnh hưởng: CRUD tests có thể chạy trực tiếp trên SQLite migration thật.

### Liên kết tài liệu liên quan
- `PLAN.md`
- `IMPLEMENTATION_TASKS.md`
- `IMPLEMENTATION_ORDER.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
