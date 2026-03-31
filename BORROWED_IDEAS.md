# BORROWED_IDEAS.md

## Mục tiêu của tài liệu

Tài liệu này liệt kê rõ:
- Nên mượn ý tưởng nào từ `codex-weave`
- Nên mượn ý tưởng nào từ `agentchattr`
- Phần nào cần tự thiết kế cho dự án của chúng ta
- Phần nào nên để lại cho các phiên bản sau

Mục tiêu là xây một hệ **nhiều Codex agent có thể nói chuyện với nhau**, nhưng không bị khóa cứng vào một fork khó bảo trì quá sớm.

---

## 1. Nên mượn từ `codex-weave`

Nguồn chính:
- https://github.com/rosem/codex-weave

### 1.1 Session chung cho nhiều agent
**Mượn:** mô hình **persistent sessions** như một “phòng chat” chung.

**Lý do:** `codex-weave` mô tả Weave sessions là nơi nhiều CLI agents có thể giao tiếp, chia sẻ ngữ cảnh và cộng tác theo thời gian thực.

**Áp dụng cho dự án:**
- Mỗi session có `session_id`
- Một session có nhiều agent tham gia
- Tin nhắn, relay, trạng thái và lịch sử đều gắn với session

### 1.2 Agent identity rõ ràng
**Mượn:** mỗi agent có tên riêng và được hiển thị cho agent khác.

**Lý do:** điều này giúp người dùng và coordinator dễ hiểu “ai đang nói”, “ai đang làm gì”, “ai vừa được giao việc”.

**Áp dụng cho dự án:**
- `agent_id`
- `display_name`
- `role`
- `is_lead`

### 1.3 Lead / non-lead model
**Mượn:** chỉ **lead** mới có quyền phát động relay và gửi control action.

**Lý do:** đây là cách đơn giản nhưng hiệu quả để tránh nhiều agent cùng điều phối lung tung.

**Áp dụng cho dự án:**
- Người dùng hoặc một agent được gán làm lead
- Lead được quyền giao việc bằng mention
- Non-lead chỉ trả lời hoặc chat bình thường, trừ khi được nâng quyền

### 1.4 Mention-based routing bằng `#agent`
**Mượn:** cú pháp `#agent` để giao việc cho agent khác trong cùng session.

**Lý do:** rất dễ học, rất phù hợp cho bản MVP.

**Áp dụng cho dự án:**
- `#builder tạo patch cho bug này`
- `#reviewer review diff vừa rồi`
- `#planner tóm tắt và chia việc tiếp`

### 1.5 Control commands tối thiểu
**Mượn:** bộ lệnh:
- `/new`
- `/interrupt`
- `/compact`

**Lý do:** đây là bộ điều khiển nhỏ nhưng đủ mạnh cho collaboration runtime.

**Áp dụng cho dự án:**
- `/new`: tạo lượt làm việc mới cho agent được mention
- `/interrupt`: dừng turn đang chạy
- `/compact`: yêu cầu compaction cho thread của agent

### 1.6 Coordinator process riêng
**Mượn:** ý tưởng có một **coordinator riêng** thay vì nhúng hết logic điều phối vào mỗi agent.

**Lý do:** giúp tách:
- phần chat/session/routing
- phần runtime Codex
- phần API công khai

**Áp dụng cho dự án:**
- `Coordinator` là service trung tâm
- Codex chỉ là execution engine
- các agent không nói trực tiếp với nhau, mà đi qua coordinator

---

## 2. Nên mượn từ `agentchattr`

Nguồn chính:
- https://github.com/bcurts/agentchattr

### 2.1 Chat server/orchestrator độc lập
**Mượn:** kiến trúc “chat server riêng”, không nhúng collaboration vào một agent duy nhất.

**Lý do:** dễ mở rộng, dễ thay engine phía dưới, dễ test độc lập.

**Áp dụng cho dự án:**
- `SessionManager`
- `Router`
- `AgentRegistry`
- `PresenceService`
- `CodexBridge`

### 2.2 Tự động kích hoạt agent khi bị mention
**Mượn:** khi agent bị mention, hệ thống tự kích hoạt agent đó đọc đúng ngữ cảnh rồi phản hồi.

**Lý do:** đây là cơ chế cốt lõi để tạo cảm giác “agent đang thật sự nói chuyện với nhau”.

**Áp dụng cho dự án:**
- Router phát hiện `#agent`
- Tạo một trigger cho agent đích
- Agent đích nhận đúng session context và lịch sử liên quan
- Sau đó phản hồi lại session chung

### 2.3 Loop guard
**Mượn:** cơ chế chặn vòng lặp khi hai agent gọi qua gọi lại quá nhiều lần.

**Lý do:** không có loop guard thì agent A và B có thể tranh luận vô tận, đốt token và làm session khó kiểm soát.

**Áp dụng cho dự án:**
- Đếm số hop liên tiếp giữa các agent trong một session
- Dừng relay khi vượt ngưỡng
- Yêu cầu lead hoặc người dùng xác nhận để tiếp tục

### 2.4 Channels
**Mượn:** ý tưởng tổ chức hội thoại theo **channel** thay vì chỉ một luồng chat duy nhất.

**Lý do:** khi dự án lớn dần, session phẳng rất dễ rối.

**Áp dụng cho dự án:**
- V1 có thể chỉ có 1 channel mặc định
- V2 thêm nhiều channel như:
  - `#general`
  - `#debug`
  - `#review`
  - `#planning`

### 2.5 Presence / heartbeat / offline queue
**Mượn:** cơ chế agent online/offline, heartbeat định kỳ, và queue tin nhắn khi agent vắng mặt.

**Lý do:** coordinator không nên giả định agent luôn sống.

**Áp dụng cho dự án:**
- Mỗi agent gửi heartbeat
- Nếu timeout thì đánh dấu offline
- Tin nhắn gửi cho agent offline được xếp hàng
- Khi agent online lại, coordinator có thể phát tiếp

### 2.6 Roles
**Mượn:** role bền cho từng agent.

**Lý do:** role giúp specialization đơn giản mà không cần logic quá phức tạp.

**Áp dụng cho dự án:**
- `planner`
- `builder`
- `reviewer`
- `researcher`
- `tester`

### 2.7 Jobs
**Mượn:** phân biệt chat thông thường với “công việc có trạng thái”.

**Lý do:** khi làm việc thực sự, bạn cần theo dõi một nhiệm vụ có title, trạng thái, lịch sử riêng.

**Áp dụng cho dự án:**
- Một mention có thể tạo `job`
- Job có các trạng thái như:
  - `todo`
  - `active`
  - `blocked`
  - `done`
- Job có thể map sang task nội bộ hoặc A2A task sau này

### 2.8 Rules
**Mượn:** cơ chế rule gợi ý cách làm việc của agent, nhưng con người vẫn giữ quyền phê duyệt.

**Lý do:** đây là cách an toàn để đưa quy tắc cộng tác vào hệ thống.

**Áp dụng cho dự án:**
- Rule có thể do người dùng thêm
- Agent có thể đề xuất rule
- Lead hoặc người dùng mới quyết định activate

### 2.9 Chia module rõ ràng
**Mượn:** cách chia thành các module tách biệt.

**Áp dụng cho dự án:**
- `router.py`
- `session_manager.py`
- `agent_registry.py`
- `presence.py`
- `codex_bridge.py`
- `artifacts.py`
- `a2a_adapter.py`

---

## 3. Cần tự thiết kế cho dự án của chúng ta

Đây là phần không repo nào đưa ra đúng như nhu cầu hiện tại.

### 3.1 CodexBridge
Cần tự xây một lớp bridge để nói chuyện với `codex app-server` qua `stdio` hoặc transport nội bộ.

Bridge này cần hỗ trợ tối thiểu:
- `initialize`
- `thread/start`
- `thread/resume`
- `turn/start`
- `turn/steer`
- `turn/interrupt`
- `thread/compact/start`

### 3.2 Session ↔ Agent ↔ Codex thread mapping
Cần tự định nghĩa mapping rõ ràng:
- `session` = phòng chat/cộng tác
- `agent` = một runtime logic
- `codex_thread_id` = context thực thi của agent trong session
- `turn_id` = lượt đang chạy

### 3.3 Artifact layer
Cần tự map output từ Codex thành các artifact dễ dùng:
- `final-text`
- `diff`
- `file`
- `summary`

### 3.4 A2A adapter layer
Nếu muốn mở rộng theo chuẩn A2A, cần tự xây thêm:
- Agent Card
- `message:send`
- `message:stream`
- `get task`
- `cancel`
- `subscribe`

### 3.5 State store
Cần tự thiết kế DB nội bộ, ít nhất gồm:
- `sessions`
- `agents`
- `session_members`
- `messages`
- `jobs`
- `artifacts`
- `codex_threads`
- `presence`

### 3.6 Permission / approval policy
Cần tự thêm logic:
- ai được relay
- ai được interrupt
- ai được compact
- khi nào cần user approval
- khi nào cần pause vì loop guard

---

## 4. Nên hoãn sang phiên bản sau

### 4.1 Fork Codex CLI
**Hoãn:** chưa fork Codex ngay từ đầu.

**Lý do:** chi phí bám upstream cao, không phù hợp với người mới khi sản phẩm lõi còn chưa ổn định.

### 4.2 Web UI đầy đủ
**Hoãn:** dashboard lớn, panel nhiều tab, drag-and-drop jobs.

**Lý do:** nên hoàn thiện coordinator + API + session runtime trước.

### 4.3 Structured multi-phase sessions
**Hoãn:** debate/planning/code-review templates phức tạp.

**Lý do:** đây là tính năng rất hấp dẫn, nhưng sẽ làm tăng độ phức tạp orchestration nếu thêm quá sớm.

### 4.4 Multi-tenant / cloud deployment
**Hoãn:** auth production, phân quyền nhiều người dùng, scale cloud.

**Lý do:** nên chốt bản local single-user hoặc small-team trước.

---

## 5. Bản lai được đề xuất

### V1
Mượn từ `codex-weave`:
- session
- agent name
- lead role
- `#agent`
- `/interrupt`
- `/compact`

Mượn từ `agentchattr`:
- router
- auto-trigger
- loop guard
- presence/heartbeat
- offline queue cơ bản
- module separation

Tự làm:
- `CodexBridge`
- SQLite state store
- session/agent/thread mapping

### V2
Mượn thêm từ `agentchattr`:
- channels
- roles
- jobs
- rules

Tự làm:
- artifact improvements
- A2A endpoints
- subscribe/streaming API

### V3
Tự làm:
- phase-based collaboration
- advanced policy engine
- review workflows
- cloud-friendly deployment

---

## 6. Kết luận

Dự án của chúng ta nên:
- **mượn UX cộng tác từ `codex-weave`**
- **mượn kiến trúc điều phối từ `agentchattr`**
- **tự xây lớp `CodexBridge + A2AAdapter + State Store`**

Đây là hướng cân bằng nhất giữa:
- dễ làm với người mới
- ít bị khóa vào fork khó bảo trì
- vẫn đủ mạnh để tiến tới hệ nhiều agent nói chuyện được như `codex-weave`
