# STATUS.md

### Trạng thái hiện tại
- **Ngày cập nhật:** 2026-03-31
- **Pha hiện tại:** F03 hoàn thành
- **Đang tập trung vào:** F04 - thiết lập migration framework
- **Người thực hiện:** Codex

### Đang làm
- [ ] F04 — Thiết lập migration framework
- [ ] PR03 — Thiết lập kết nối DB và migration framework

### Vừa hoàn thành
- [x] F03 — Tạo core app modules — 2026-03-31
- [x] F02 — Cấu hình toolchain và chất lượng mã nguồn — 2026-03-31
- [x] F01 — Tạo skeleton dự án — 2026-03-31
- [x] PR01 — Tạo skeleton repo và app chạy được — 2026-03-31

### Tiếp theo
- [ ] F04 — DB connection factory và migration runner
- [ ] F05 — Schema nhóm bảng nền
- [ ] PR04 — Tạo schema nhóm bảng nền

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
