# STATUS.md

### Trạng thái hiện tại
- **Ngày cập nhật:** 2026-03-31
- **Pha hiện tại:** PR04 hoàn thành
- **Đang tập trung vào:** F06 - schema runtime và lịch sử
- **Người thực hiện:** Codex

### Đang làm
- [ ] F06 — Tạo migration cho nhóm bảng runtime và lịch sử
- [ ] PR05 — Tạo schema nhóm bảng runtime và lịch sử

### Vừa hoàn thành
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
- [ ] F06 — messages, message_mentions, jobs, job_events, artifacts, approvals, presence, relay, session_events
- [ ] PR05 — Tạo schema nhóm bảng runtime và lịch sử

### Blockers / Rủi ro
- Không có

### Ghi chú quyết định gần đây
- Quyết định: Tách F05 thành 2 migration SQL nhỏ: bảng nền và index nền.
- Lý do: Giữ migration rõ ràng, dễ kiểm tra và khớp trình tự trong DB schema.
- Ảnh hưởng: F05 và PR04 có thể xác nhận bằng test migration từ DB rỗng.

### Liên kết tài liệu liên quan
- `PLAN.md`
- `IMPLEMENTATION_TASKS.md`
- `IMPLEMENTATION_ORDER.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
