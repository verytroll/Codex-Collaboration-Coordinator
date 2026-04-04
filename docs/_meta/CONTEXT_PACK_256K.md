# Context Pack (256K) — Codex Collaboration Coordinator

Tài liệu này tối ưu cho **context window ~256K**, nghĩa là bạn có thể vừa nạp đủ bối cảnh (docs) **vừa** còn chỗ cho:

- đọc code liên quan
- suy luận / lập kế hoạch
- viết patch + test + cập nhật docs

Mục tiêu: giúp “onboard lại dự án” và triển khai thay đổi mà **không phải nạp toàn bộ `docs/`**.

---

## 1) Quy tắc ngân sách context

Khuyến nghị (tương đối):

- **Docs**: 15–30% context (đủ để định hướng, tránh drift).
- **Code liên quan**: 50–70% context (đủ để sửa đúng chỗ).
- **Reasoning + output**: 10–25% context (đủ để ra quyết định + mô tả thay đổi rõ).

Nếu thấy mình đang “đọc docs cho đã” mà chưa mở file code nào: dừng lại, chuyển sang **`rg` → mở module cụ thể → implement**.

---

## 2) Read set mặc định (tối thiểu nhưng đủ dùng)

Luôn đọc (hầu hết tasks):

1. `README.md` (setup, scripts, entrypoints)
2. `AGENTS.md` (quy tắc kiến trúc + ranh giới service/repo + test/lint discipline)
3. `docs/planning/STATUS.md` (pha đang làm + next step)
4. **(tuỳ chọn, khi cần vận hành)** `docs/operations/LOCAL_SETUP.md`, `docs/operator/OPERATOR_UI.md`

Chỉ mở các docs lớn khi “có câu hỏi cụ thể”:

- API/payload/HTTP contract → `docs/reference/API.md`
- boundary/flow/why-this-exists → `docs/reference/ARCHITECTURE.md`
- DB table/migration/persistence → `docs/reference/DB_SCHEMA.md`

Tránh nạp mặc định:

- `docs/planning/archive/*` (trừ khi cần truy vết lịch sử Vx).

---

## 3) Bản đồ hệ thống (tóm tắt 5 phút)

### 3.1 Hệ thống này là gì?

**Codex Collaboration Coordinator** là một server (FastAPI) đóng vai trò *control plane* cho collaboration:

- quản lý **session**
- quản lý **agents** và **participants**
- nhận **messages** (mention `#agent` và command `/new`…)
- tạo/điều phối **jobs**
- lưu **artifacts** + **approvals**
- cung cấp **streaming (SSE)** + operator surfaces
- tích hợp Codex qua `CodexBridge` (JSON-RPC client + subprocess manager)

### 3.2 Kiến trúc “coordinator-first” (invariants)

- API routes mỏng: wiring + validation + gọi service.
- Business logic nằm trong `app/services/`.
- Persistence chỉ qua `app/repositories/` (không raw SQL trong services).
- Tất cả tương tác Codex đi qua `app/codex_bridge/` (không gọi Codex trực tiếp từ API routes).
- Loop protection và policy/rbac không được bypass “cho nhanh”.

### 3.3 Các thực thể chính (mental model)

- `session`: “phòng” cộng tác.
- `agent`: persona/runtime đại diện cho một tác nhân.
- `participant`: agent tham gia một session, kèm role/policy.
- `message`: input/output trong transcript; có thể chứa mention hoặc command.
- `job`: đơn vị công việc chạy qua CodexBridge; có lifecycle rõ.
- `artifact`: kết quả (text/diff/file/json/log…).
- `approval`: yêu cầu người vận hành duyệt một hành động nhạy cảm.

---

## 4) “User flows” quan trọng (khi debug hoặc implement)

### 4.1 Giao việc bằng mention

- Người dùng/agent gửi message có `#Builder`/`#builder`…
- Mention được resolve theo: `display_name` → `role` → `id` (case-insensitive).
- Nếu policy cho phép, coordinator tạo job cho agent được mention.

Gợi ý code hotspots:

- parse: `app/services/message_parser.py`
- resolve: `app/services/mention_router.py`
- route + create job: `app/services/message_routing.py`, `app/services/command_handler.py`

### 4.2 Lệnh dạng `/command`

Các command hợp lệ hiện tại:

- `/new` (tạo job mới cho target agent, thường kèm mention)
- `/interrupt` (dừng job hiện tại)
- `/compact` (giảm context của job)
- `/review` (yêu cầu review)

### 4.3 Approval loop

Khi job cần duyệt, lifecycle có thể chuyển sang `auth_required`, và operator/user phải accept/decline.

Operator UI shell hỗ trợ approve/reject theo operator routes, còn public route dùng accept/decline.

### 4.4 Streaming và “incident history”

- Có SSE cho session/job streams (phục vụ operator + public surfaces).
- Operator activity feed có cursor + resume semantics (`since_sequence`, `Last-Event-ID`).

---

## 5) “Đường chạy” khi bạn muốn làm một thay đổi

### 5.1 Khi thay đổi API/contract

1. `docs/reference/API.md`: đọc phần liên quan payload/status.
2. Tìm router: `app/api/*.py` (dùng `rg` theo path).
3. Tìm service: `app/services/*.py`.
4. Tìm repo: `app/repositories/*.py`.
5. Sửa tests gần nhất: `tests/integration/*` hoặc `tests/unit/*`.
6. Chạy: `.\scripts\test.ps1`, `.\scripts\lint.ps1`.

### 5.2 Khi thay đổi persistence

1. `docs/reference/DB_SCHEMA.md` (table, constraint, invariant).
2. Migrations: `app/db/migrations/*.sql`.
3. Repo layer: `app/repositories/*`.
4. Integration tests về migrations/repo.

### 5.3 Khi thay đổi operator workflows/UI shell

1. `docs/operator/OPERATOR_UI.md` (routes + contract UI).
2. UI: `ui/index.html` (thin shell; chủ yếu render + call operator endpoints).
3. API operator: `app/api/operator_*.py`.
4. Tests operator + smoke script.

---

## 6) Quickstart (local)

- Start: `.\scripts\dev.ps1`
- Seed demo: `.\scripts\seed.ps1`
- Operator UI: `http://127.0.0.1:8000/operator`
- Smoke: `.\scripts\smoke.ps1`

---

## 7) Anti-patterns (để giữ context sạch)

- Đừng mở đồng thời `ARCHITECTURE.md` + `API.md` + `DB_SCHEMA.md` + toàn bộ planning archive nếu chưa có câu hỏi cụ thể.
- Đừng copy/paste toàn bộ file lớn vào context; hãy mở đúng section cần thiết.
- Đừng “sửa nhanh” trong `app/api/*` để tránh service/repo boundaries (sẽ drift nhanh).

