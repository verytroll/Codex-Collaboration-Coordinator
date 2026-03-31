# STATUS.md

### Trạng thái hiện tại
- **Ngày cập nhật:** 2026-03-31
- **Pha hiện tại:** F04 hoàn thành
- **Đang tập trung vào:** F05 - schema nhóm bảng nền
- **Người thực hiện:** Codex

### Đang làm
- [ ] F05 — Tạo migration cho nhóm bảng nền
- [ ] PR04 — Tạo schema nhóm bảng nền

### Vừa hoàn thành
- [x] F04 — Thiết lập migration framework — 2026-03-31
- [x] F03 — Tạo core app modules — 2026-03-31
- [x] F02 — Cấu hình toolchain và chất lượng mã nguồn — 2026-03-31
- [x] F01 — Tạo skeleton dự án — 2026-03-31
- [x] PR01 — Tạo skeleton repo và app chạy được — 2026-03-31

### Tiếp theo
- [ ] F05 — sessions, agents, agent_runtimes, session_participants
- [ ] PR05 — Tạo schema nhóm bảng runtime và lịch sử

### Blockers / Rủi ro
- Không có

### Ghi chú quyết định gần đây
- Quyết định: Dựng skeleton tối thiểu trước khi thêm toolchain và business logic.
- Lý do: Giữ PR01 nhỏ, dễ review, và tạo nền ổn định cho F02.
- Ảnh hưởng: Có thể import `app.main` và xác nhận cấu trúc dự án ngay từ đầu.

### Liên kết tài liệu liên quan
- `PLAN.md`
- `IMPLEMENTATION_TASKS.md`
- `IMPLEMENTATION_ORDER.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
