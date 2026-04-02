# STATUS.md

### Trạng thái hiện tại
- Ngày cập nhật: 2026-04-02
- Pha hiện tại: V6 implementation
- Đã hoàn tất: PR48 / F46 - interop certification và external adoption baseline
- Người thực hiện: Codex

### Đang làm

### Vừa hoàn thành
- [x] F46 - Interop certification và external adoption baseline - 2026-04-02
- [x] PR48 - Interop certification và external adoption baseline - 2026-04-02
- [x] F45 - Realtime streaming transport - 2026-04-02
- [x] PR47 - Realtime streaming transport - 2026-04-02
- [x] F44 - Durable runtime và persistence boundary - 2026-04-02
- [x] PR46 - Durable runtime và persistence boundary - 2026-04-02
- [x] F43 - Identity và team RBAC cơ bản - 2026-04-02
- [x] PR45 - Identity và team RBAC cơ bản - 2026-04-02
- [x] F42 - Operator actions và audit trail - 2026-04-02
- [x] PR44 - Operator actions và audit trail - 2026-04-02
- [x] F41 - V5 release closure và baseline discipline - 2026-04-02
- [x] F40 - Small-team deployment profile và release packaging - 2026-04-01
- [x] PR42 - Small-team deployment profile và release packaging - 2026-04-01
- [x] F39 - A2A interoperability và adoption kit - 2026-04-01
- [x] PR41 - A2A interoperability và adoption kit - 2026-04-01
- [x] F38 - Realtime operator surface - 2026-04-01
- [x] PR40 - Realtime operator surface - 2026-04-01
- [x] F37 - Thin operator UI shell - 2026-04-01
- [x] PR39 - Thin operator UI shell - 2026-04-01
- [x] F36 - Access boundary và external safety baseline - 2026-04-01
- [x] PR38 - Access boundary và external safety baseline - 2026-04-01
- [x] F35 - Deployment surface và external readiness tối thiểu - 2026-04-01
- [x] PR37 - Deployment surface và external readiness tối thiểu - 2026-04-01
- [x] F34 - Release readiness và operational safety - 2026-04-01
- [x] PR36 - Release readiness và operational safety - 2026-04-01
- [x] F33 - Thêm telemetry và observability theo thời gian - 2026-04-01
- [x] PR35 - Telemetry và observability - 2026-04-01
- [x] F32 - Hardening và reliability cho public/orchestration/runtime surface - 2026-04-01
- [x] PR34 - Hardening và reliability - 2026-04-01
- [x] Chốt thứ tự triển khai V4 (`IMPLEMENTATION_ORDER_V4.md`) - 2026-04-01
- [x] Chuẩn bị backlog V4 (`IMPLEMENTATION_TASKS_V4.md`) - 2026-04-01
- [x] Chốt kế hoạch V4 (`PLAN_V4.md`) - 2026-04-01
- [x] F31 - Tạo advanced policy engine và conditional automation - 2026-04-01
- [x] PR33 - Advanced policy engine và conditional automation - 2026-04-01
- [x] F30 - Mở rộng operator dashboard/debug surface - 2026-04-01
- [x] PR32 - Operator dashboard/debug expansion - 2026-04-01
- [x] F29 - Thêm runtime pools và isolated work contexts - 2026-04-01
- [x] PR31 - Runtime pools và isolated work contexts - 2026-04-01
- [x] F28 - Nâng cấp review orchestration và gated phase transitions - 2026-04-01
- [x] PR30 - Advanced review orchestration và phase gates - 2026-04-01
- [x] F27 - Tạo session templates và orchestration presets - 2026-04-01
- [x] PR29 - Session templates và orchestration presets - 2026-04-01
- [x] F25 - Chuẩn hóa A2A public API v1 trên nền adapter bridge - 2026-04-01
- [x] F26 - Thêm public subscribe/push event model cho task - 2026-04-01
- [x] PR27 - A2A public API v1 - 2026-04-01
- [x] PR28 - Public subscribe/push event surface - 2026-04-01
- [x] Chuẩn bị backlog V3 - 2026-03-31
- [x] F24 - Thêm phase presets và experimental A2A adapter bridge - 2026-03-31
- [x] F23 - Tạo review mode và structured relay templates - 2026-03-31
- [x] F22 - Nâng cấp artifacts và transcript export - 2026-03-31
- [x] F21 - Tạo rules engine cơ bản và manual activation flow - 2026-03-31
- [x] F20 - Nâng cấp advanced jobs và offline queue tối thiểu - 2026-03-31
- [x] F19 - Bổ sung roles, permissions và participant policy rõ hơn - 2026-03-31
- [x] F18 - Thêm channel structure cho session - 2026-03-31
- [x] F17 - Hoàn thiện system status, diagnostics và debug surface - 2026-03-31
- [x] PR19 - System status, diagnostics và debug surface - 2026-03-31
- [x] PR18 - Hoàn thiện MVP, docs và A2A-ready surface - 2026-03-31

### Tiếp theo
- [ ] Roadmap sau V6

### Blockers / Rủi ro
- Chưa có blocker hiện tại
- Rủi ro chính là docs, package và status drift khỏi baseline release thật
- Rủi ro phụ là tăng deployment complexity cho small-team profile trước khi smoke/release path đủ rõ

### Kiểm chứng gần nhất
- `pytest` - 104 passed - 2026-04-02
- `python -m ruff check app tests` - passed - 2026-04-02
- `python -m compileall app tests` - passed - 2026-04-02
- `python -m ruff format --check app tests` - passed - 2026-04-02
- `.\scripts\release.ps1` - passed - 2026-04-02

### Liên kết tài liệu liên quan
- `PLAN.md`
- `PLAN_V2.md`
- `PLAN_V3.md`
- `PLAN_V4.md`
- `PLAN_V5.md`
- `IMPLEMENTATION_TASKS.md`
- `IMPLEMENTATION_TASKS_V2.md`
- `IMPLEMENTATION_TASKS_V3.md`
- `IMPLEMENTATION_TASKS_V4.md`
- `IMPLEMENTATION_TASKS_V5.md`
- `IMPLEMENTATION_ORDER.md`
- `IMPLEMENTATION_ORDER_V2.md`
- `IMPLEMENTATION_ORDER_V3.md`
- `IMPLEMENTATION_ORDER_V4.md`
- `IMPLEMENTATION_ORDER_V5.md`
- `IMPLEMENTATION_TASKS_V6.md`
- `IMPLEMENTATION_ORDER_V6.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `API.md`
- `DB_SCHEMA.md`
